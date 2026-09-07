# Problem Definition — TOKI

**Status:** approved problem framing  
**Terakhir diperbarui:** 6 September 2026

## 1. Konteks

Anak usia dini membutuhkan kesempatan berbicara yang sering, responsif, menyenangkan, dan sesuai tahap perkembangan. Di rumah, kualitas dan frekuensi stimulasi dapat tidak konsisten karena keterbatasan waktu, pengetahuan, materi, atau akses pendampingan. Pada saat yang sama, speech recognition dan conversational AI umum tidak dirancang untuk variasi pelafalan, jeda, disfluency, kebisingan, serta kebutuhan keselamatan anak usia 3–6 tahun.

Proposal awal TOKI menawarkan perangkat berbentuk panda dengan percakapan, computer vision, adaptasi, dan dashboard orang tua. Proposal tersebut adalah hipotesis awal, bukan kewajiban teknis. Masalah yang harus diselesaikan bukan “membuat mainan AI serba bisa”, melainkan membangun loop belajar yang terbatas, aman, terukur, dan reliabel.

## 2. Problem statement

> Bagaimana TOKI dapat memberikan aktivitas stimulasi berbicara berbahasa Indonesia yang singkat dan telah disetujui ahli, memahami upaya anak yang sangat bervariasi tanpa menghukum ketidakpastian sistem, memberi feedback yang sesuai, memperbarui bukti belajar yang dapat dijelaskan, dan tetap menyelesaikan aktivitas dengan aman ketika AI, perangkat, atau jaringan gagal?

## 3. Pengguna dan kebutuhan

| Pengguna | Kebutuhan utama | Risiko bila gagal |
|---|---|---|
| Anak usia ±3–6 | prompt singkat, respons cepat, retry ramah, feedback positif | frustrasi, label salah, konten tidak sesuai |
| Orang tua/wali | kontrol consent, ringkasan mudah dipahami, batas klaim yang jujur | salah memahami data sebagai diagnosis |
| Guru/ahli PAUD/psikologi | kurikulum dan safety language dapat ditinjau/versioned | konten tidak sesuai perkembangan |
| Operator tim | status sistem, trace, recovery, release yang reproducible | demo gagal dan sulit didiagnosis |
| Juri | dampak produk, alasan penggunaan AI, bukti metrik, reliability | sistem terlihat sebagai gimmick teknologi |

## 4. Jobs to be done

### Anak

“Ketika berlatih berbicara, bantu saya mencoba kata atau frasa melalui aktivitas yang menyenangkan, tunggu respons saya, dan bantu lagi tanpa membuat saya merasa salah ketika suara saya tidak dipahami.”

### Orang tua

“Setelah anak menggunakan TOKI, tunjukkan aktivitas dan bukti partisipasi secara sederhana agar saya tahu cara melanjutkan stimulasi, tanpa memberikan klaim medis.”

### Tim kompetisi

“Saat demo, buktikan satu loop belajar nyata di hardware, perlihatkan nilai tambah AI yang terukur, dan pulihkan kegagalan jaringan/model tanpa kehilangan keselamatan atau integritas state.”

## 5. Root causes

1. **Variabilitas child speech.** Pitch, artikulasi, kecepatan, kosakata, dan disfluency membuat ASR dewasa tidak otomatis cocok.
2. **Kesalahan sistem mudah disalahartikan sebagai kesalahan anak.** Confidence provider tidak selalu terkalibrasi dan transcript bukan ground truth.
3. **Open-ended generation sulit dikontrol.** Chatbot bebas dapat keluar kurikulum, terlalu panjang, tidak sesuai umur, atau menghasilkan konten yang tidak memiliki provenance.
4. **AI pipeline menambah latency dan failure point.** ASR, retrieval, LLM, filter, TTS, CV, dan device delivery dapat gagal secara independen.
5. **Data anak sangat sensitif.** Audio, video, identitas, dan inferred behavior menimbulkan risiko privasi yang tidak sebanding jika disimpan tanpa kebutuhan.
6. **Data adaptasi terbatas.** Kompetisi tidak menyediakan histori cukup untuk membenarkan BKT/DKT atau training model khusus sejak awal.
7. **Demo environment tidak stabil.** Venue noise, Wi-Fi, quota, perangkat, dan provider cloud bisa gagal.

## 6. Desired outcome

Sistem yang berhasil harus:

- menyelesaikan satu aktivitas approved dari prompt sampai progress projection;
- menggunakan deterministic policy untuk state, correctness, safety, mastery, dan fallback;
- menggunakan AI hanya untuk speech/perception/ambiguity yang terukur;
- mengizinkan setiap AI component `ABSTAIN` tanpa menghukum anak;
- memberi respons singkat dan child-appropriate dengan provenance;
- menyimpan derived learning events, bukan raw media secara default;
- menjelaskan perubahan mastery dengan reason code;
- mempertahankan core activity dalam mode cloud maupun local degraded;
- menunjukkan p50/p95 latency, fallback, safety, dan release evidence kepada juri.

## 7. Scope

### In scope

- lima domain kurikulum awal: bagian tubuh, keluarga, hewan, warna, dan emosi;
- aktivitas speech-stimulation yang adult-mediated;
- ESP32-S3 audio/playback serta camera snapshot terpicu;
- session state machine, curriculum engine, assessment, feedback, mastery;
- ASR/TTS adapters, optional semantic resolver/paraphraser, triggered CV;
- parent progress API dan observability/evaluation;
- cloud primary dan local demo twin.

### Out of scope

- diagnosis, terapi, clinical score, atau klaim menyembuhkan speech delay;
- unrestricted conversation, web search, atau general-purpose assistant;
- penggunaan mandiri tanpa pengawasan orang dewasa;
- face/speaker identification dan emotion inference sebagai ground truth;
- continuous surveillance dan raw-media retention secara default;
- automatic curriculum publication;
- runtime autonomous agents;
- training model dari interaksi anak secara otomatis;
- platform berskala besar, microservices, Kafka, atau Kubernetes sebelum kompetisi.

## 8. Risiko kegagalan utama

| Risiko | Dampak | Respons desain |
|---|---|---|
| ASR salah/timeout | feedback atau label salah | rules/context, `UNCERTAIN`, retry satu kali, choice/imitation fallback |
| LLM keluar schema/kurikulum | konten tidak aman/tidak valid | structured output, deterministic validation, template fallback |
| TTS lambat/gagal | anak menunggu | cache-first, dynamic TTS hanya pada miss, canned asset |
| CV salah | aktivitas membingungkan | curated labels, threshold, freshness, `UNKNOWN`; tidak memblokir speech loop |
| State race/duplicate callback | duplicate mastery/playback | `state_version`, `turn_id`, idempotency, ACK, stale-result discard |
| DB/jaringan gagal | state hilang/demo berhenti | atomic transaction, bounded buffer, reconnect/resume, local demo twin |
| PII/raw media di log | pelanggaran privasi | minimization, redaction, ephemeral media, privacy tests |
| Terlalu banyak fitur | vertical slice tidak selesai | competition cut-line dan promotion gate |

## 9. Pertanyaan yang dijawab melalui evaluasi

1. Provider ASR mana yang memberi expected-concept accuracy dan latency terbaik pada audio child/device-like Indonesia?
2. Apakah semantic resolver meningkatkan penyelesaian ambiguous turn dibanding rules-only baseline tanpa menaikkan false-incorrect dan p95 secara tidak dapat diterima?
3. Apakah paraphrasing meningkatkan naturalness sementara seluruh output tetap valid, approved, singkat, dan aman?
4. Apakah object detection memiliki per-class performance dan unknown false-positive rate yang cukup untuk satu aktivitas demo?
5. Apakah seluruh named failure mencapai safe bounded state?
6. Apakah cloud dan local profile memakai kontrak yang sama dan bisa menyelesaikan aktivitas inti?

## 10. Success metrics

### Release gates wajib

- 0 high-severity unsafe output pada frozen `child-safety-300-v1`;
- 100% required escalation memilih reviewed canned content;
- 100% child-facing contract valid;
- 100% normal generated response memiliki valid curriculum provenance;
- 0 raw child media/direct identifier pada normal logs;
- 100% failure-injection case berakhir pada safe bounded state;
- 200-turn replay tanpa state corruption atau duplicate mastery update;
- 30-minute soak tanpa unrecovered disconnect/resource growth;
- primary ASR/TTS dipilih berdasarkan benchmark, bukan reputasi vendor;
- realistic end-to-end p95 dilaporkan apa adanya, dengan target awal endpoint-to-first-audio ≤3 detik.

### Product/evaluation metrics

- completed-turn dan completed-activity rate;
- independent/hinted/assisted outcome;
- re-prompt, abstention, fallback, dan session-completion rate;
- ASR WER/CER serta expected-concept accuracy;
- assessment macro F1, selective accuracy/coverage, dan false-incorrect rate;
- response schema/provenance/age-appropriateness;
- p50/p95/p99 latency per stage dan end-to-end;
- parent comprehension terhadap progress explanation;
- cost per completed activity.

## 11. Assumptions dan TBD

### Assumption aktif

- waktu implementasi sekitar 12 minggu dan final 2–4 November 2026;
- lima module awal tetap menjadi ruang kurikulum utama;
- tim dapat memperoleh review ahli terhadap content, safety, dan rubric;
- data child speech yang governed terbatas, sehingga tidak cukup untuk training foundation model;
- venue internet dapat tidak stabil;
- hardware utama ESP32-S3 dengan kemampuan audio, speaker, display/gesture, dan snapshot kamera.

### TBD yang harus diselesaikan pemilik terkait

- rubric resmi LIDM final dan constraint presentasi/demo;
- dataset consented yang benar-benar tersedia;
- codec, chunk size, sample rate, device memory, dan firmware contract final;
- provider ASR/TTS/LLM pemenang benchmark dan region deployment;
- threshold/per-class labels CV;
- retention period, guardian consent text, dan deletion/export workflow;
- formula rule-based mastery yang disetujui ahli;
- repository URL dan status implementasi aktual.

TBD bukan izin untuk menebak secara permanen. Agent boleh membuat default yang reversible untuk memulai, tetapi harus menandai dan menguji asumsi tersebut.

