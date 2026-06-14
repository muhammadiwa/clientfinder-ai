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

  // Prospects
  prospects: {
    title: "Prospek",
    subtitle: "Daftar semua prospek yang sudah ditemukan",
    add: "Tambah prospek",
    noProspects: "Belum ada prospek",
    noProspectsHint: "Mulai dengan menjalankan Scout untuk menemukan prospek baru",
    totalCount: "Total prospek",
    avgScore: "Skor rata-rata",
  },

  // Pipeline
  pipeline: {
    title: "Pipeline",
    subtitle: "Lihat prospek berdasarkan status pipeline",
    stages: {
      new: "Baru",
      scored: "Sudah dinilai",
      contacted: "Dihubungi",
      qualified: "Terkualifikasi",
      won: "Menang",
      lost: "Kalah",
    },
  },

  // Scout
  scout: {
    title: "Scout",
    subtitle: "Temukan prospek baru dari Google, Maps, Twitter, Threads",
    runJob: "Jalankan Scout",
    jobsInQueue: "Pekerjaan dalam antrian",
    presets: "Preset pencarian",
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
