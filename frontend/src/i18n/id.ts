/**
 * i18n — Bahasa Indonesia (id) is the primary language.
 *
 * R2: All user-facing copy should be in Bahasa Indonesia.
 * Pattern: typed strings object + a t() helper. No library
 * dependency (KISS — react-i18next is overkill for a single
 * locale + a few dozen keys; can be added later if needed).
 *
 * Usage:
 *   import { t } from "@/i18n/id";
 *   <h1>{t.outreach.title}</h1>
 *
 * To add a new key: add it to STRINGS below. TypeScript will
 * flag any missing keys at compile time.
 */

const STRINGS = {
  // Common
  common: {
    appName: "ClientFinder",
    appTagline: "AI Agent",
    save: "Simpan",
    cancel: "Batal",
    confirm: "Konfirmasi",
    delete: "Hapus",
    edit: "Edit",
    close: "Tutup",
    back: "Kembali",
    next: "Selanjutnya",
    submit: "Kirim",
    loading: "Memuat…",
    error: "Terjadi kesalahan",
    retry: "Coba lagi",
    search: "Cari",
    filter: "Filter",
    clear: "Bersihkan",
    yes: "Ya",
    no: "Tidak",
    notAvailable: "—",
    viewAll: "Lihat semua",
  },

  // Nav (Sidebar)
  nav: {
    dashboard: "Dashboard",
    scout: "Scout",
    prospects: "Prospek",
    pipeline: "Pipeline",
    outreach: "Outreach",
    analytics: "Analitik",
    settings: "Pengaturan",
  },

  // Auth
  auth: {
    signIn: "Masuk",
    signOut: "Keluar",
    signUp: "Daftar",
    email: "Email",
    password: "Kata sandi",
    fullName: "Nama lengkap",
    forgotPassword: "Lupa kata sandi?",
    invalidCredentials: "Email atau kata sandi salah",
    signedOut: "Berhasil keluar",
    signedIn: "Berhasil masuk",
    noAccount: "Belum punya akun?",
    haveAccount: "Sudah punya akun?",
  },

  // Dashboard
  dashboard: {
    title: "Selamat datang kembali",
    subtitle:
      "Berikut yang terjadi di pipeline lead generation Anda hari ini.",
    live: "Langsung",
    viewPipeline: "Lihat pipeline",
    newSearch: "Pencarian baru",
    totalProspects: "Total prospek",
    allTime: "Sepanjang waktu",
    hotLeads: "Prospek panas",
    hotLeadsDesc: "Skor 80+",
    contacted: "Dihubungi",
    contactedDesc: "Outreach terkirim",
    won: "Menang",
    wonDesc: "{pct}% konversi",
    new: "Baru",
    scored: "Sudah dinilai",
    contactedLabel: "Dihubungi",
    wonLabel: "Menang",
    pipelineActivity: "Aktivitas pipeline",
    pipelineActivityDesc: "Aktivitas harian lintas tahap dalam 14 hari terakhir",
    couldNotLoad: "Tidak dapat memuat aktivitas",
    couldNotLoadDesc: "Periksa koneksi Anda atau masuk lagi",
    noActivity: "Belum ada aktivitas",
    noActivityDesc: "Jalankan Scout untuk mulai melihat aktivitas di sini",
    runFirstScout: "Jalankan Scout pertama",
    leadQuality: "Kualitas prospek",
    leadQualityDesc: "Distribusi per grade",
    total: "total",
    pipelineActivation: "Aktivasi pipeline",
    pipelineActivationDesc: "% prospek yang sudah melewati tahap 'Baru'",
    winRate: "Tingkat kemenangan",
    winRateDesc: "% dari total prospek yang closing",
    dropOff: "Drop-off",
    dropOffDesc: "% prospek yang ditandai sebagai Kalah",
    topProspects: "Prospek teratas",
    topProspectsDesc: "Prospek dengan skor tertinggi, siap untuk outreach",
    company: "Perusahaan",
    industry: "Industri",
    status: "Status",
    score: "Skor",
    grade: "Grade",
    noProspects: "Belum ada prospek",
    noProspectsDesc: "Jalankan Scout untuk menemukan bisnis yang cocok dengan ICP Anda",
    startProspecting: "Mulai prospek",
  },

  // Prospects
  prospects: {
    title: "Prospek",
    subtitle: "Daftar semua prospek yang sudah ditemukan",
    add: "Tambah prospek",
    noProspects: "Tidak ada prospek ditemukan",
    noProspectsHint: "Coba kata kunci lain atau hapus filter",
    emptyHint: "Jalankan Scout untuk menemukan bisnis yang butuh layanan software",
    allStatus: "Semua",
    newStatus: "Baru",
    scoredStatus: "Sudah dinilai",
    contactedStatus: "Dihubungi",
    repliedStatus: "Dibalas",
    wonStatus: "Menang",
    lostStatus: "Kalah",
    totalCount: "Total prospek",
    avgScore: "Skor rata-rata",
    searchPlaceholder: "Cari berdasarkan perusahaan, email…",
    searchAriaLabel: "Cari prospek",
    noMatch: "Tidak ada prospek ditemukan",
  },

  // Pipeline
  pipeline: {
    title: "Pipeline",
    subtitle: "Lihat prospek berdasarkan status pipeline",
    stages: {
      new: "Baru",
      enriching: "Sedang diperkaya",
      scored: "Sudah dinilai",
      contacted: "Dihubungi",
      replied: "Dibalas",
      won: "Menang",
      lost: "Kalah",
    },
    manualAddSoon: "Tambah manual segera hadir",
  },

  // Scout
  scout: {
    title: "Scout",
    subtitle: "Temukan prospek baru dari Google, Maps, Twitter, Threads",
    runJob: "Jalankan Scout",
    jobsInQueue: "Pekerjaan dalam antrian",
    presets: "Preset pencarian",
    sources: {
      google: "Google Search",
      googleDesc: "SearXNG meta-search (Google + DuckDuckGo + Bing + Brave)",
      maps: "Google Maps",
      mapsDesc: "Playwright Chromium headless — bisnis, alamat, telepon",
      twitter: "Twitter / X",
      twitterDesc: "Hadir di T4.5 — butuh cookies sesi yang sudah login",
      threads: "Threads",
      threadsDesc: "Hadir di T4.5 — butuh cookies sesi yang sudah login",
    },
    statusLabels: {
      pending: "Menunggu",
      running: "Berjalan",
      completed: "Selesai",
      failed: "Gagal",
    },
    keywordsRequired: "Kata kunci wajib diisi",
    failedToCreate: "Gagal membuat pekerjaan",
    jobRequeued: "Pekerjaan dimasukkan kembali ke antrian",
    couldNotRetry: "Tidak dapat mengulang pekerjaan",
    jobDeleted: "Pekerjaan dihapus. Prospek yang sudah ditambahkan tetap ada.",
    couldNotDelete: "Tidak dapat menghapus pekerjaan",
    locationPlaceholder: "Jakarta, Bandung, Jabodetabek…",
    polling: "Polling setiap 3s selama pekerjaan berjalan…",
    idle: "Diam — mulai pekerjaan untuk melihat pembaruan langsung",
    noJobs: "Belum ada pekerjaan",
    noJobsDesc: "Mulai pekerjaan Scout pertama untuk melihat aktivitas di sini",
    noDiscoveries: "Belum ada penemuan Scout",
    noDiscoveriesDesc: "Mulai pekerjaan Scout dan prospek baru akan muncul di sini",
  },

  // Prospect detail
  prospectDetail: {
    couldNotLoad: "Tidak dapat memuat prospek",
    notFound: "Tidak ditemukan",
    reAnalyze: "Analisis ulang",
    reAnalyzing: "Menganalisis ulang…",
    generateHooks: "Buat hook",
    generating: "Membuat…",
    reAnalyzeFailed: "Analisis ulang gagal",
    hookGenFailed: "Pembuatan hook gagal",
    hookCopied: "Hook disalin ke clipboard",
    copyFailed: "Gagal menyalin",
    notYetAnalyzed: "Belum dianalisis",
    notYetAnalyzedDesc: "Jalankan pipeline analis untuk menghitung rincian skor 5 faktor",
    factors: {
      painSeverity: "Tingkat keparahan masalah",
      painSeverityDesc: "Rata-rata keparahan × jumlah masalah",
      solutionFit: "Kecocokan solusi",
      solutionFitDesc: "Industri + layanan yang cocok",
      signalStrength: "Kekuatan sinyal",
      signalStrengthDesc: "Sinyal + kepadatan masalah",
      budgetIndicator: "Indikator anggaran",
      budgetIndicatorDesc: "Industri + lokasi (proxy)",
      timingUrgency: "Urgensi waktu",
      timingUrgencyDesc: "Kesegaran (turun setelah 90 hari)",
    },
    tech: {
      framework: "Framework",
      hosting: "Hosting",
      noAudit: "Belum ada audit teknologi",
      noAuditDesc: "Jalankan analis untuk sidik jari situs web",
    },
  },

  // Outreach
  outreach: {
    title: "Outreach",
    subtitle: "Antrean tinjauan R10 — semua pesan butuh persetujuan",
    compose: "Buat pesan baru",
    pendingReview: "Menunggu tinjauan",
    approved: "Disetujui",
    sent: "Terkirim",
    replied: "Dibalas",
    failed: "Gagal",
    approve: "Setujui",
    reject: "Tolak",
    send: "Kirim",
    delete: "Hapus",
    generate: "Buat dengan AI",
    rejectReason: "Alasan penolakan (wajib)",
    bulkApprove: "Setujui semua",
    bulkReject: "Tolak semua",
    noMessages: "Tidak ada pesan",
    allCaughtUp: "Semua sudah selesai",
  },

  // Analytics
  analytics: {
    title: "Analitik",
    subtitle: "Performa outreach dan pipeline",
    period7d: "7 hari terakhir",
    period30d: "30 hari terakhir",
    period90d: "90 hari terakhir",
    totalLeads: "Total prospek",
    messagesSent: "Pesan terkirim",
    replyRate: "Tingkat balasan",
    winRate: "Tingkat kemenangan",
    leadGen: "Generasi prospek",
    leadGenDesc: "Volume dari Scout + distribusi grade + kecepatan",
    outreachSection: "Outreach",
    outreachSectionDesc: "Volume per channel + corong persetujuan + balasan",
    pipelineSection: "Pipeline",
    pipelineSectionDesc: "Distribusi prospek per status + win rate",
    operational: "Operasional",
    operationalDesc: "Aktivitas terbaru, penggunaan LLM, tingkat keberhasilan",
  },

  // Status
  status: {
    pending: "Menunggu",
    inProgress: "Berjalan",
    completed: "Selesai",
    failed: "Gagal",
  },

  // NotFound
  notFound: {
    title: "Halaman tidak ditemukan",
    description: "Halaman yang Anda cari tidak ada.",
    goHome: "Ke dashboard",
  },

  // Toasts
  toast: {
    saved: "Berhasil disimpan",
    deleted: "Berhasil dihapus",
    approved: "Pesan disetujui",
    rejected: "Pesan ditolak",
    sent: "Pesan terkirim",
    failed: "Gagal",
    copied: "Disalin ke clipboard",
  },
} as const;

export type Strings = typeof STRINGS;
export const t = STRINGS;
