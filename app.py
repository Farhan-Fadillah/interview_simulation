import streamlit as st
import json
import uuid
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
from openai import OpenAI
from supabase import create_client, Client

# ── Config & Setup ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Interviewer & Analytics", page_icon="🎯", layout="wide")

# Load secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
OPENAI_BASE_URL = st.secrets.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
MODEL = "gpt-4o"

SYSTEM_PROMPT = """Anda adalah "AI Business Simulation Interviewer" yang sedang melakukan sesi wawancara simulasi bisnis untuk mengevaluasi kemampuan problem-solving mahasiswa calon peserta bootcamp Alumni.

Topik simulasi sesi ini: "{interview_topic}"
Profil perusahaan Alumni: "{company_profile}"

━━━━━━━━━━━━━━━━━━━━━━━
PERAN & KARAKTER ANDA
━━━━━━━━━━━━━━━━━━━━━━━
Anda berperan sebagai manajer senior yang profesional, kritis, namun tetap suportif. Anda:
* Berbicara dalam Bahasa Indonesia yang santun dan profesional.
* Tidak pernah memberikan jawaban atau solusi kepada kandidat.
* Tidak pernah memuji jawaban secara berlebihan. Cukup "Baik, lanjut..." atau "Menarik. Sekarang...".
* Selalu fokus menggali PROSES BERPIKIR, bukan hanya jawaban akhir.

━━━━━━━━━━━━━━━━━━━━━━━
ATURAN WAJIB SESI INTERVIEW
━━━━━━━━━━━━━━━━━━━━━━━
* Ajukan hanya satu pertanyaan per respons. Tidak boleh menggabungkan 2 pertanyaan sekaligus.
* Analisis jawaban kandidat secara INTERNAL sebelum membuat pertanyaan berikutnya.
* Semua pertanyaan dan teks yang tampil ke kandidat WAJIB dalam Bahasa Indonesia.
* Minimum 5 pertanyaan, maksimum 10 pertanyaan per sesi.
* Setelah pertanyaan ke-8, tambahkan kalimat di field "interviewer_note": "Ketik 'stop interview' jika kamu sudah selesai."
* Terus ajukan pertanyaan sampai evaluasi cukup. Setelah itu berikan pesan: "Interview selesai — silakan ketik stop interview."

━━━━━━━━━━━━━━━━━━━━━━━
TRIGGER PROBING & PRESSURE TEST
━━━━━━━━━━━━━━━━━━━━━━━
* Lakukan probing jika jawaban terlalu umum, tidak ada framework, atau tanpa target audiens yang jelas.
* Wajib sisipkan 1x Pressure Test (budget nol, deadline mepet, data tidak ada) di tengah sesi.

━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — WAJIB DIIKUTI
━━━━━━━━━━━━━━━━━━━━━━━
Output HANYA objek JSON tanpa markdown backtick apapun.

{
  "stop_interview": false,
  "question": "string atau null",
  "interviewer_note": "string atau null",
  "is_probing": false,
  "is_pressure_test": false,
  "current_state": "opening|exploration|pressure_test|user_centricity|closing",
  "question_number": 1,
  "internal_evaluation": {
    "logical_structure": null,
    "feasibility": null,
    "user_centricity": null,
    "professional_tone": null
  },
  "final_scores": null
}

Saat stop_interview=true, final_scores harus diisi dengan skor 1-5 dan summary:
{
  "logical_structure": 1-5,
  "feasibility": 1-5,
  "user_centricity": 1-5,
  "professional_tone": 1-5,
  "total": sum,
  "tier_recommendation": "Tier 1 - Lulus Otomatis | Tier 2 - Lulus Bersyarat | Tier 3 - Revisi / Tunggu",
  "summary": "2-3 kalimat evaluasi"
}
"""

# ── Helper Functions ──────────────────────────────────────────────────────────
def analyze_sentiment(text: str) -> dict:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Analyze sentiment and return ONLY JSON: {\"label\": \"positive|neutral|negative\", \"score\": 0.0-1.0}"},
                {"role": "user", "content": text}
            ],
            temperature=0, max_tokens=50
        )
        return json.loads(resp.choices[0].message.content.strip())
    except:
        return {"label": "neutral", "score": 0.5}

def save_session_db(data: dict):
    supabase.table('sessions').upsert(data).execute()

def save_turn_db(data: dict):
    supabase.table('turns').insert(data).execute()

# ── UI Navigation ─────────────────────────────────────────────────────────────
page = st.sidebar.radio("Navigasi", ["Simulasi Interview", "Analytics Dashboard"])

# PAGE 1: SIMULASI INTERVIEW
if page == "Simulasi Interview":
    st.title("🎯 AI Business Simulation Interviewer")

    if 'session_id' not in st.session_state:
        st.session_state.session_id = None

    # Form Setup
    if not st.session_state.session_id:
        with st.form("setup_form"):
            name = st.text_input("Nama Kandidat")
            topic = st.selectbox("Topik Simulasi", [
                "Strategi pertumbuhan pengguna baru (user acquisition) platform edukasi",
                "Optimasi konversi dari trial ke berbayar (free-to-paid conversion)",
                "Peningkatan retensi dan engagement pengguna aktif"
            ])
            profile = "Alumni adalah platform edukasi online bootcamp teknologi. 50.000+ alumni di 5 kota besar."
            
            submitted = st.form_submit_button("Mulai Interview")
            if submitted and name:
                st.session_state.session_id = str(uuid.uuid4())
                st.session_state.name = name
                st.session_state.topic = topic
                st.session_state.profile = profile
                st.session_state.started_at = datetime.now(timezone.utc).isoformat()
                st.session_state.messages = [] # For UI display
                st.session_state.llm_history = [{"role": "system", "content": SYSTEM_PROMPT.format(interview_topic=topic, company_profile=profile)}]
                st.session_state.question_count = 1
                st.session_state.is_done = False
                
                # Simpan data awal sesi ke DB agar Foreign Key di tabel turns terpenuhi
                initial_session = {
                    "session_id": st.session_state.session_id,
                    "candidate_name": st.session_state.name,
                    "interview_topic": st.session_state.topic,
                    "company_profile": st.session_state.profile,
                    "started_at": st.session_state.started_at
                }
                save_session_db(initial_session)
                st.rerun()

    # Chat Interface
    else:
        st.subheader(f"Sesi: {st.session_state.name}")
        st.caption(f"Topik: {st.session_state.topic}")

        # Display UI messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg.get("note"):
                    st.caption(f"📌 *{msg['note']}*")

        # Initial LLM Call (Start)
        if len(st.session_state.messages) == 0 and not st.session_state.is_done:
            with st.spinner("Menyiapkan pertanyaan pembuka..."):
                st.session_state.llm_history.append({"role": "user", "content": "Mulai sesi interview."})
                resp = client.chat.completions.create(
                    model=MODEL, messages=st.session_state.llm_history, temperature=0.7, response_format={"type": "json_object"}
                )
                output = json.loads(resp.choices[0].message.content.strip())
                st.session_state.llm_history.append({"role": "assistant", "content": json.dumps(output)})
                
                # Render first question
                q = output.get("question", "Silakan mulai.")
                note = output.get("interviewer_note")
                st.session_state.messages.append({"role": "assistant", "content": q, "note": note})
                st.rerun()

        # Input Chat
        if not st.session_state.is_done:
            user_input = st.chat_input("Tulis jawaban Anda di sini...")
            if user_input:
                # 1. Tampilkan jawaban user
                st.session_state.messages.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.write(user_input)

                # 2. Proses LLM
                with st.spinner("Menganalisis jawaban..."):
                    sentiment = analyze_sentiment(user_input)
                    st.session_state.llm_history.append({"role": "user", "content": user_input})
                    
                    resp = client.chat.completions.create(
                        model=MODEL, messages=st.session_state.llm_history, temperature=0.7, response_format={"type": "json_object"}
                    )
                    output = json.loads(resp.choices[0].message.content.strip())
                    st.session_state.llm_history.append({"role": "assistant", "content": json.dumps(output)})

                    # 3. Simpan turn ke DB
                    turn_data = {
                        "session_id": st.session_state.session_id,
                        "turn_number": st.session_state.question_count,
                        "question": output.get("question", ""),
                        "answer": user_input,
                        "is_probing": output.get("is_probing", False),
                        "is_pressure_test": output.get("is_pressure_test", False),
                        "current_state": output.get("current_state", ""),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sentiment_label": sentiment.get("label", "neutral"),
                        "sentiment_score": sentiment.get("score", 0.5)
                    }
                    save_turn_db(turn_data)

                    # Update counters & logic
                    st.session_state.question_count = output.get("question_number", st.session_state.question_count + 1)
                    
                    if output.get("stop_interview"):
                        st.session_state.is_done = True
                        fs = output.get("final_scores", {})
                        
                        # Save session to DB
                        session_data = {
                            "session_id": st.session_state.session_id,
                            "candidate_name": st.session_state.name,
                            "interview_topic": st.session_state.topic,
                            "company_profile": st.session_state.profile,
                            "started_at": st.session_state.started_at,
                            "ended_at": datetime.now(timezone.utc).isoformat(),
                            "total_questions": st.session_state.question_count,
                            "logical_structure": fs.get("logical_structure", 0),
                            "feasibility": fs.get("feasibility", 0),
                            "user_centricity": fs.get("user_centricity", 0),
                            "professional_tone": fs.get("professional_tone", 0),
                            "total_score": fs.get("total", 0),
                            "tier": fs.get("tier_recommendation", ""),
                            "summary": fs.get("summary", "")
                        }
                        save_session_db(session_data)
                        
                        st.session_state.messages.append({"role": "assistant", "content": "Sesi interview telah selesai. Terima kasih."})
                        st.rerun()
                    else:
                        q = output.get("question", "")
                        note = output.get("interviewer_note")
                        st.session_state.messages.append({"role": "assistant", "content": q, "note": note})
                        st.rerun()

        # End Screen
        if st.session_state.is_done:
            st.success("Sesi selesai dan data telah disimpan ke Supabase!")
            if st.button("Mulai Sesi Baru"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()


# PAGE 2: ANALYTICS DASHBOARD
elif page == "Analytics Dashboard":
    st.title("📊 Alumni Interview Analytics")

    # Fetch Data
    sessions_res = supabase.table('sessions').select('*').order('started_at', desc=True).execute()
    sessions_data = sessions_res.data

    if not sessions_data:
        st.info("Belum ada data sesi interview. Silakan jalankan simulasi terlebih dahulu.")
    else:
        df = pd.DataFrame(sessions_data)
        
        # Bersihkan data Null/None untuk keperluan filter
        df['candidate_name'] = df['candidate_name'].fillna("Unknown")
        df['interview_topic'] = df['interview_topic'].fillna("Unknown")
        df['tier'] = df['tier'].fillna("Belum Selesai")

        # ── FILTERING PANEL ──
        st.markdown("### 🔍 Filter Data")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            filter_nama = st.multiselect("Nama Kandidat", options=sorted(df['candidate_name'].unique()))
        with f_col2:
            filter_topik = st.multiselect("Topik Interview", options=sorted(df['interview_topic'].unique()))
        with f_col3:
            filter_tier = st.multiselect("Tier Hasil", options=sorted(df['tier'].unique()))

        # Apply Filters
        filtered_df = df.copy()
        if filter_nama:
            filtered_df = filtered_df[filtered_df['candidate_name'].isin(filter_nama)]
        if filter_topik:
            filtered_df = filtered_df[filtered_df['interview_topic'].isin(filter_topik)]
        if filter_tier:
            filtered_df = filtered_df[filtered_df['tier'].isin(filter_tier)]

        st.divider()

        if filtered_df.empty:
            st.info("Tidak ada data yang cocok dengan filter saat ini.")
        else:
            # Memisahkan data yang sudah komplit (ada skor akhir) untuk perhitungan KPI dan chart
            completed_df = filtered_df.dropna(subset=['total_score'])

            # ── KPIs ──
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Sessions (Filtered)", len(filtered_df))
            
            pass_rate = 0
            if not completed_df.empty:
                passed = len(completed_df[completed_df['tier'].str.contains('Tier 1|Tier 2', na=False)])
                pass_rate = (passed / len(completed_df)) * 100
            
            col2.metric("Pass Rate (Tier 1 & 2)", f"{pass_rate:.1f}%")
            col3.metric("Avg Total Score", f"{completed_df['total_score'].mean():.1f}" if not completed_df.empty else "0")
            col4.metric("Completed Sessions", len(completed_df))

            st.markdown("<br>", unsafe_allow_html=True)

            # ── DEEP ANALYTICS CHARTS ──
            c_chart1, c_chart2 = st.columns(2)
            
            with c_chart1:
                st.subheader("Distribusi Rekomendasi (Tier)")
                if not completed_df.empty:
                    tier_counts = completed_df['tier'].value_counts().reset_index()
                    tier_counts.columns = ['Tier', 'Jumlah']
                    fig_tier = px.pie(tier_counts, names='Tier', values='Jumlah', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
                    st.plotly_chart(fig_tier, use_container_width=True)
                else:
                    st.write("Belum ada sesi yang selesai untuk diplot.")

            with c_chart2:
                st.subheader("Rata-rata Skor per Dimensi (Max 5)")
                if not completed_df.empty:
                    avg_dims = completed_df[['logical_structure', 'feasibility', 'user_centricity', 'professional_tone']].mean().reset_index()
                    avg_dims.columns = ['Dimensi Penilaian', 'Skor Rata-rata']
                    # Mempercantik nama label dimensi
                    avg_dims['Dimensi Penilaian'] = avg_dims['Dimensi Penilaian'].str.replace('_', ' ').str.title()
                    
                    fig_dims = px.bar(avg_dims, x='Skor Rata-rata', y='Dimensi Penilaian', orientation='h', text='Skor Rata-rata')
                    fig_dims.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                    fig_dims.update_layout(xaxis=dict(range=[0, 5.5])) # Range max 5 tapi diberi ruang untuk label
                    st.plotly_chart(fig_dims, use_container_width=True)
                else:
                    st.write("Belum ada sesi yang selesai untuk diplot.")

            # Menambahkan chart Distribusi Topik
            st.subheader("Distribusi Topik Interview")
            topic_counts = filtered_df['interview_topic'].value_counts().reset_index()
            topic_counts.columns = ['Topik', 'Jumlah Sesi']
            fig_topic = px.bar(topic_counts, x='Topik', y='Jumlah Sesi', color='Topik')
            fig_topic.update_layout(showlegend=False)
            st.plotly_chart(fig_topic, use_container_width=True)

            st.divider()

            # ── Data Table ──
            st.subheader("Detail Sesi Interview")
            display_df = filtered_df[['candidate_name', 'interview_topic', 'total_score', 'tier', 'started_at']].copy()
            display_df['started_at'] = pd.to_datetime(display_df['started_at']).dt.strftime('%Y-%m-%d %H:%M')
            display_df.rename(columns={
                'candidate_name': 'Nama Kandidat', 'interview_topic': 'Topik', 
                'total_score': 'Total Skor', 'tier': 'Tier', 'started_at': 'Tanggal Mulai'
            }, inplace=True)
            st.dataframe(display_df, use_container_width=True)

            st.divider()
            
            # ── AI Strategic Insight (Generative AI Analytics) ──
            st.subheader("🤖 AI Strategic Insight (Berdasarkan Filter)")
            st.markdown("AI akan membaca kumpulan data kandidat yang sedang Anda filter saat ini untuk menemukan pola kompetensi, kelemahan umum, dan memberikan masukan HR tingkat lanjut.")
            
            if st.button("Generate Analisis Mendalam", type="primary"):
                if completed_df.empty:
                    st.warning("Data yang di-filter tidak memiliki sesi yang telah selesai (Completed) untuk dianalisis.")
                else:
                    with st.spinner("Menganalisis tren performa kandidat..."):
                        avg_scores_dict = avg_dims.set_index('Dimensi Penilaian')['Skor Rata-rata'].to_dict()
                        tier_dict = tier_counts.set_index('Tier')['Jumlah'].to_dict()
                        
                        # Mengambil sampel summary evaluasi kandidat untuk konteks kualitatif (maks 10 sampel agar tidak over-token)
                        sample_summaries = completed_df['summary'].dropna().head(10).tolist()
                        
                        stats_summary = {
                            "total_kandidat_dinilai": len(completed_df),
                            "distribusi_tier": tier_dict,
                            "rata_rata_dimensi_skor": avg_scores_dict,
                            "sampel_catatan_evaluasi": sample_summaries
                        }
                        
                        prompt = f"""Anda adalah Chief HR Officer (CHRO) dan Ahli Rekrutmen. 
Berdasarkan data agregat dari kelompok kandidat yang sedang di-filter ini:
{json.dumps(stats_summary, ensure_ascii=False)}

Tuliskan Analisis Kohort Mendalam (maksimal 3 paragraf). Fokus pada:
1. Analisis kekuatan dan kelemahan kolektif berdasarkan rata-rata dimensi skor (contoh: jika user_centricity rendah, apa dampaknya?).
2. Pola yang terlihat dari sampel catatan evaluasi.
3. Rekomendasi program pelatihan atau fokus pertanyaan wawancara selanjutnya untuk kelompok (cohort) dengan profil seperti ini."""
                        
                        resp = client.chat.completions.create(
                            model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.5
                        )
                        st.info(resp.choices[0].message.content.strip())
