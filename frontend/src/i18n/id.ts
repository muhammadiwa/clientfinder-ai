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
    openMenu: "Buka menu",
    closeMenu: "Tutup menu",
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
    signedOutLocally: "Berhasil keluar dari sesi lokal (server tidak merespons)",
    signedIn: "Berhasil masuk",
    noAccount: "Belum punya akun?",
    haveAccount: "Sudah punya akun?",
    welcomeBack: "Selamat datang kembali",
    accountCreated: "Akun berhasil dibuat. Silakan masuk.",
    couldNotCreate: "Tidak dapat membuat akun",
    passwordTooShort: "Kata sandi harus minimal 8 karakter",
    networkError: "Kesalahan jaringan. Silakan coba lagi.",
    signInFailed: "Gagal masuk",
    signUpFailed: "Gagal mendaftar",
  },

  // Topbar
  topbar: {
    searchProspects: "Cari prospek…",
    searchAriaLabel: "Cari prospek",
    notifications: "Notifikasi",
    userMenu: "Menu pengguna",
  },

  // Profile (Settings)
  profile: {
    title: "Profil",
    subtitle: "Informasi akun Anda",
    identity: "Identitas",
    identityDesc: "Avatar dan info dasar Anda",
    account: "Akun",
    accountDesc: "Email, nama, dan field akun lainnya",
    fullName: "Nama lengkap",
    email: "Email",
    role: "Peran",
    userId: "ID Pengguna",
    joined: "Bergabung {date}",
    edit: "Edit",
    profileEditingComing: "Edit profil akan tersedia setelah multi-user support di T8.",
  },

  // Settings / Team
  team: {
    multiUserComing: "Multi-user support segera hadir di T8",
  },

  // Settings / Danger
  danger: {
    exportAllData: "Export semua data",
    rotateApiKey: "Rotate API key",
    deleteAccount: "Hapus akun",
  },

  // ConfirmDialog
  confirmDialog: {
    ariaClose: "Tutup",
    defaultCancelText: "Batal",
    defaultConfirmText: "Konfirmasi",
  },

  // Form errors (shared across pages)
  formErrors: {
    required: "{field} wajib diisi",
    emailInvalid: "Format email tidak valid",
    passwordTooShort: "Kata sandi minimal 8 karakter",
    passwordMismatch: "Kata sandi tidak cocok",
    minLength: "{field} minimal {min} karakter",
    maxLength: "{field} maksimal {max} karakter",
    networkError: "Kesalahan jaringan. Coba lagi.",
    serverError: "Terjadi kesalahan pada server. Coba lagi nanti.",
    rateLimited: "Terlalu banyak percobaan. Coba lagi dalam beberapa menit.",
    notFound: "Tidak ditemukan",
    unauthorized: "Sesi berakhir. Silakan masuk lagi.",
    forbidden: "Anda tidak punya akses untuk aksi ini.",
    conflict: "Data sudah ada",
    validationFailed: "Data tidak valid",
    unknown: "Terjadi kesalahan yang tidak diketahui",
    // Field-level
    fieldRequired: "wajib diisi",
    fieldTooShort: "terlalu pendek (min {min} karakter)",
    fieldTooLong: "terlalu panjang (max {max} karakter)",
    fieldInvalid: "format tidak valid",
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
    // T8.5++++++: hardcoded audit replacements
    retry: "Coba lagi",
    delete: "Hapus",
  },

  // Prospect detail
  prospectDetail: {
    couldNotLoad: "Tidak dapat memuat prospek",
    notFound: "Tidak ditemukan",
    reAnalyze: "Analisis ulang",
    reAnalyzing: "Menganalisis ulang…",
    generateHooks: "Buat hook",
    regenerate: "Buat ulang",
    generating: "Membuat…",
    reAnalyzeFailed: "Analisis ulang gagal",
    hookGenFailed: "Pembuatan hook gagal",
    hookCopied: "Hook disalin ke clipboard",
    copyFailed: "Gagal menyalin",
    failedToLoadDetail: "Gagal memuat detail",
    notYetAnalyzed: "Belum dianalisis",
    notYetAnalyzedDesc: "Jalankan pipeline analis untuk menghitung rincian skor 5 faktor",
    reasoning: "Alasan",
    noPainPoints: "Tidak ada masalah terdeteksi",
    noPainPointsDesc:
      "Prospek sudah digital-first, atau analis belum dijalankan",
    noHooksYet: "Belum ada hook",
    noHooksYetDesc:
      "Klik 'Buat hook' untuk mendapatkan 3 sudut outreach yang dipersonalisasi",
    confidenceScore: "Skor kepercayaan",
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
      cms: "CMS",
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
    sent: "Terkirim",
    sentTotal: "Terkirim (total)",
    replied: "Dibalas",
    failed: "Gagal",
    approve: "Setujui",
    reject: "Tolak",
    send: "Kirim",
    delete: "Hapus",
    generate: "Buat dengan AI",
    rejectReason: "Alasan penolakan (wajib)",
    reasonOptional: "Alasan (opsional)",
    bulkApprove: "Setujui semua",
    bulkReject: "Tolak semua",
    bulkApprovedToast: "{ok} dari {total} pesan disetujui",
    bulkRejectedToast: "{ok} dari {total} pesan ditolak",
    bulkApproveAllFailed: "Semua persetujuan gagal",
    bulkRejectAllFailed: "Semua penolakan gagal",
    noMessages: "Tidak ada pesan",
    allCaughtUp: "Semua sudah selesai",
    sentCheckTab: "Terkirim (cek tab Sent untuk status)",
    pickProspectHook: "Pilih prospek + hook dulu",
    generateFirst: "Buat dulu pesannya",
    copyFailed: "Gagal menyalin",
    // Toasts
    failedToLoad: "Gagal memuat pesan",
    approvedToast: "Disetujui",
    approvalFailed: "Persetujuan gagal",
    rejectedToast: "Ditolak",
    rejectFailed: "Penolakan gagal",
    sentToast: "Terkirim (cek tab Sent untuk status)",
    sendFailed: "Pengiriman gagal",
    submitted: "Dikirim untuk persetujuan",
    submitFailed: "Pengajuan gagal",
    deleted: "Dihapus",
    deleteFailed: "Gagal menghapus (pesan terkirim tidak bisa dihapus)",
    generateFailed: "Pembuatan gagal",
    createFailed: "Pembuatan gagal",
    subjectRequired: "Subjek wajib diisi",
    bodyRequired: "Body wajib diisi",
    bodyTooShort: "Body terlalu pendek (min 20 karakter)",
    // Search
    searchPlaceholder: "Cari subject, body, atau company…",
    searchProspectPlaceholder: "Cari prospek…",
    noProspectsMatch: "Tidak ada prospek yang cocok",
    // Composer
    channelEmail: "Email",
    channelWhatsapp: "WhatsApp",
    templatePlaceholder: "Pakai AI secara default",
    noTemplates: "Belum ada template",
    // Dialog
    rejectTitle: "Tolak pesan ini?",
    rejectDescription:
      "Pesan akan ditandai sebagai ditolak dan tidak akan dikirim. Opsional: berikan alasan untuk tim.",
    // Bulk
    selected: "dipilih",
    cancel: "Batal",
    // T8.5++++++: hardcoded string audit replacements
    approveShortcut: "Setujui (A)",
    rejectShortcut: "Tolak (R)",
    sendShortcut: "Kirim sekarang (S)",
    submitForApproval: "Kirim untuk persetujuan",
    retrySend: "Coba kirim ulang",
    noResults: "Tidak ada hasil",
    noDraftsYet: "Belum ada draf",
    nothingSentYet: "Belum ada yang dikirim",
    noFailures: "Tidak ada kegagalan",
    deleteConfirmTitle: "Hapus pesan ini?",
    confirmDelete: "Hapus",
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
    gradeDistribution: "Distribusi grade",
    sourceQuality: "Kualitas sumber",
    timeToEnrich: "Waktu sampai diperkaya",
    avgTime: "Rata-rata",
    p50Time: "P50 (median)",
    p90Time: "P90",
    dailyVolume: "Volume harian",
    byChannel: "Per channel",
    byStage: "Per tahap",
    approvalFunnel: "Corong persetujuan",
    noLeads: "Belum ada prospek",
    noMessagesSent: "Belum ada pesan terkirim",
    noProspects: "Belum ada prospek",
    noActivity: "Belum ada aktivitas",
    noActivityPeriod: "Tidak ada aktivitas di periode ini",
    basedOnN: "Berdasarkan {n} prospek yang diperkaya",
    total: "total",
    recentActivity: "Aktivitas terbaru",
    llmUsage: "Penggunaan LLM",
    taskSuccessRates: "Tingkat keberhasilan tugas",
    successRateLow:
      "Di bawah 80% — periksa log Celery atau failure rate di T8.",
    sentVsReplied: "Terkirim vs Dibalas per hari",
    pipelineByStage: "Distribusi prospek per tahap",
    won: "Menang",
    avgScoreWon: "Skor rata-rata (menang)",
    avgScoreWonDesc: "Proxy untuk kualitas deal",
    realDealSize: "Ukuran deal asli di T8",
    success24h: "Last 24h",
    estTokens: "Est. tokens",
    totalCalls: "Total panggilan",
    // Funnel
    drafts: "Draf",
    pending: "Menunggu",
    approved: "Disetujui",
    delivered: "Terkirim",
    sentFunnel: "Terkirim",
    repliedFunnel: "Dibalas",
    approvalRate: "Tingkat persetujuan",
    // Grade
    unscored: "Belum dinilai",
    aGrade: "Grade A",
    bGrade: "Grade B",
    cGrade: "Grade C",
    dGrade: "Grade D",
    // Time
    timeAgo: "{n} hari lalu",
    // Sections
    sendApproveEngage: "Kirim · setujui · engage",
    stageConversion: "Tahap · konversi · kecepatan",
    activityLlmSuccess: "Aktivitas · LLM · tingkat keberhasilan",
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
export default STRINGS;

// Re-export from the locale-aware index so all existing
// `import { t } from "@/i18n/id"` call sites keep working
// (T8.5++++++: language toggle)
export { t, useT, useLocaleStore } from "./index";
export type { Locale } from "./index";
