# Jurnal 7 Kebiasaan - Dashboard (Flask)

**Judul:** jurnal 7 kebiasaan anak indonesia hebat — SMK Diponegoro Tulakan

Ini adalah aplikasi dashboard sederhana berbasis Flask untuk Thonny.
Fitur utama:
- Login: admin / guru / siswa (role-based)
- Siswa: input harian 7 kebiasaan
- Guru: menambah siswa yang dibimbing, edit/hapus data siswa bimbingan, melihat & export hasil bimbingan (CSV/XLSX)
- Admin: menambah/ubah/hapus guru & siswa, melihat semua data, membuat grup

**Persyaratan** (install di Thonny Python):
- Flask (`pip install flask`)
- pandas (`pip install pandas`)
- openpyxl (opsional, untuk export .xlsx) (`pip install openpyxl`)

**Cara menjalankan**:
1. Buka Thonny. Pastikan dependencies terinstall.
2. Ekstrak `jurnal7_dashboard.zip` dan buka foldernya.
3. Jalankan `app.py` (Run). Aplikasi akan berjalan pada http://127.0.0.1:5000
4. Login default:
   - admin / password: `admin123`
   - guru1 / password: `guru123`
   - siswa1 / password: `siswa123`

**Catatan**: Ini adalah contoh aplikasi untuk penggunaan pendidikan. Sesuaikan validasi dan keamanan
untuk produksi (TLS, CSRF protection, stronger password policies).
