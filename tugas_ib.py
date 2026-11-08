
from dataclasses import dataclass

#Basis pengetahuan (Production Memory)
SALIENCE = {"Rendah": 1, "Sedang": 2, "Tinggi": 3, "Tertinggi": 4}


@dataclass(frozen=True)
class Rule:
    id: str
    lhs: tuple          # semua kondisi (AND)
    rhs: str            # fakta yang ditambahkan
    prioritas: str

    @property
    def salience(self):
        return SALIENCE[self.prioritas]

    @property
    def order(self):
        return int(self.id[1:])


RULES = [
    Rule("R1", ("Semua Situs Tidak Bisa Dibuka",), "Cek Router", "Rendah"),
    Rule("R2", ("Lampu Internet Router Merah",), "Gangguan Provider", "Sedang"),
    Rule("R3", ("Kecepatan Sangat Lambat",), "Gangguan Provider", "Sedang"),
    Rule("R4", ("Gangguan Provider", "Tagihan Sudah Dibayar"), "Lapor ke Provider", "Tinggi"),
    Rule("R5", ("Perangkat Lain Juga Offline",), "Gangguan Provider", "Sedang"),
    Rule("R6", ("Semua Situs Tidak Bisa Dibuka", "Hanya Laptop Ini Bermasalah"),
         "Masalah pada Laptop", "Tinggi"),
    Rule("R7", ("Gangguan Provider",), "Gunakan Tethering Sementara", "Rendah"),
    Rule("R8", ("Cek Router", "Router Terasa Panas"), "Matikan Router 10 Menit", "Tertinggi"),
]

FAKTA_AWAL = [
    "Semua Situs Tidak Bisa Dibuka",
    "Perangkat Lain Juga Offline",
    "Tagihan Sudah Dibayar",
]



#Forward chaining
def kunci_urut(rule):
    """Urutan pertimbangan: salience (besar dulu), specificity (kondisi
    terbanyak dulu), lalu nomor aturan (kecil dulu)."""
    return (-rule.salience, -len(rule.lhs), rule.order)


def forward_chaining(rules, fakta_awal):
    wm = list(fakta_awal)          # working memory (urut masuk)
    sudah_fire = set()             # refractoriness: aturan hanya sekali
    jejak = []
    it = 0
    while True:
        it += 1
        # Match / preselection + refractoriness
        conflict_set = [r for r in rules
                        if r.id not in sudah_fire
                        and all(c in wm for c in r.lhs)]
        # Aturan yang cocok tetapi RHS-nya sudah ada tidak berguna lagi;
        # tetap dihitung sebagai konflik sesuai definisi, tetapi tetap fire
        if not conflict_set:
            jejak.append(dict(it=it, cs=[], dipilih=None, tambah=None, wm=list(wm)))
            break
        urut = sorted(conflict_set, key=kunci_urut)
        dipilih = urut[0]
        sudah_fire.add(dipilih.id)
        baru = dipilih.rhs if dipilih.rhs not in wm else None
        if baru:
            wm.append(baru)
        jejak.append(dict(it=it, cs=urut, dipilih=dipilih, tambah=baru,
                          wm=list(wm)))
    return wm, jejak


def alasan_pemilihan(urut):
    """Jelaskan kenapa aturan pertama di conflict set terpilih."""
    if len(urut) == 1:
        return "Hanya satu aturan di conflict set."
    a, b = urut[0], urut[1]
    if a.salience != b.salience:
        return f"Salience: {a.id} ({a.prioritas}) > {b.id} ({b.prioritas})."
    if len(a.lhs) != len(b.lhs):
        return (f"Salience sama ({a.prioritas}); specificity: {a.id} punya "
                f"{len(a.lhs)} kondisi > {b.id} punya {len(b.lhs)}.")
    return (f"Salience sama ({a.prioritas}) dan specificity sama "
            f"({len(a.lhs)} kondisi); rule order: {a.id} < {b.id}.")


def cetak_forward(wm, jejak):
    print("=" * 78)
    print("(a) & (c) FORWARD CHAINING + CONFLICT RESOLUTION")
    print("=" * 78)
    print("Urutan pertimbangan: salience -> specificity -> rule order "
          "(refractoriness aktif)\n")
    print("Fakta awal:")
    for f in FAKTA_AWAL:
        print(f"  - {f}")
    print()
    print(f"{'Iter':<5}{'Conflict set (terurut)':<26}{'Dipilih':<9}"
          f"Perubahan Working Memory")
    print("-" * 78)
    for j in jejak:
        cs = "{" + ", ".join(r.id for r in j["cs"]) + "}" if j["cs"] else "{ }"
        if j["dipilih"]:
            tambah = f"+ ({j['tambah']})" if j["tambah"] else "(tidak ada fakta baru)"
            print(f"{j['it']:<5}{cs:<26}{j['dipilih'].id:<9}{tambah}")
        else:
            print(f"{j['it']:<5}{cs:<26}{'-':<9}berhenti, tidak ada aturan yang cocok")
    print()

    print("Iterasi dengan konflik (conflict set > 1 aturan):")
    for j in jejak:
        if len(j["cs"]) > 1:
            detail = ", ".join(
                f"{r.id}[{r.prioritas}, {len(r.lhs)} kondisi]" for r in j["cs"])
            print(f"  Iterasi {j['it']}: {detail}")
            print(f"    -> pilih {j['dipilih'].id}. {alasan_pemilihan(j['cs'])}")
    print()

    print("Isi Working Memory di akhir:")
    for f in wm:
        tanda = "(awal)" if f in FAKTA_AWAL else "(hasil inferensi)"
        print(f"  - {f} {tanda}")
    print()
    print("Kesimpulan baru yang dapat ditarik:")
    for f in wm:
        if f not in FAKTA_AWAL:
            print(f"  * {f}")
    tidak = [r for r in RULES if r.rhs not in wm]
    print("\nAturan yang tidak pernah fire:")
    for r in RULES:
        if r.id not in {j['dipilih'].id for j in jejak if j['dipilih']}:
            kurang = [c for c in r.lhs if c not in wm]
            print(f"  - {r.id}: kondisi belum terpenuhi -> {kurang}")
    print()



#Backward chaining

class BackwardChainer:
    def __init__(self, rules, fakta):
        self.rules = rules
        self.fakta = set(fakta)
        self.terbukti = set()
        self.gagal = set()
        self.log = []

    def _p(self, depth, teks):
        self.log.append("  " * depth + teks)

    def find_out(self, goal, depth=0, stack=()):
        self._p(depth, f"FindOut({goal})")
        if goal in self.fakta:
            self._p(depth + 1, f"'{goal}' ada di Fakta Awal -> TERBUKTI")
            return True
        if goal in self.terbukti:
            self._p(depth + 1, f"'{goal}' sudah terbukti sebelumnya -> TERBUKTI")
            return True
        if goal in self.gagal:
            self._p(depth + 1, f"'{goal}' sudah pernah gagal -> GAGAL")
            return False
        if goal in stack:               # cegah loop
            self._p(depth + 1, f"'{goal}' sedang dibuktikan (loop) -> GAGAL")
            return False

        kandidat = [r for r in self.rules if r.rhs == goal]
        if not kandidat:
            self._p(depth + 1, f"Tidak ada aturan dengan RHS '{goal}' dan bukan "
                               f"fakta awal -> GAGAL")
            self.gagal.add(goal)
            return False
        self._p(depth + 1, "RULE-LIST = {" + ", ".join(r.id for r in kandidat) + "}")

        for r in kandidat:
            if self.monitor(r, depth + 1, stack + (goal,)):
                self.terbukti.add(goal)
                self._p(depth + 1, f"'{goal}' TERBUKTI melalui {r.id}")
                return True
        self.gagal.add(goal)
        self._p(depth + 1, f"Semua aturan untuk '{goal}' gagal -> GAGAL")
        return False

    def monitor(self, rule, depth, stack):
        self._p(depth, f"Monitor({rule.id}): IF {' AND '.join(rule.lhs)} "
                       f"THEN {rule.rhs}")
        for kond in rule.lhs:
            if not self.find_out(kond, depth + 1, stack):
                self._p(depth + 1, f"{rule.id} tidak dapat dieksekusi "
                                   f"('{kond}' gagal)")
                return False
        self._p(depth + 1, f"Semua kondisi {rule.id} terpenuhi -> eksekusi {rule.id}")
        return True


def cetak_backward(goal):
    print("=" * 78)
    print(f"(b) BACKWARD CHAINING: goal = '{goal}'")
    print("=" * 78)
    bc = BackwardChainer(RULES, FAKTA_AWAL)
    hasil = bc.find_out(goal)
    print("\n".join(bc.log))
    print()
    print(f"HASIL: goal '{goal}' ->", "TERBUKTI" if hasil else "GAGAL")
    print()
    print("Rantai pembuktian (dari goal ke fakta awal):")
    print("  Lapor ke Provider  <-R4-  Gangguan Provider  +  Tagihan Sudah Dibayar")
    print("  Gangguan Provider  <-R5-  Perangkat Lain Juga Offline  (fakta awal)")
    print("  Tagihan Sudah Dibayar                                  (fakta awal)")
    print()



if __name__ == "__main__":
    wm, jejak = forward_chaining(RULES, FAKTA_AWAL)
    cetak_forward(wm, jejak)
    cetak_backward("Lapor ke Provider")
