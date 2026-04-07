ROUNDS = 11
def add_relation(out, variables):
    out.write(f"{', '.join(variables)}\n")

with open("relations.txt", "w", encoding="utf-8") as out:
    out.write("connection relations\n")
    for t in range(ROUNDS):
        # вихід:
        # Z_t = S_{15+t} xor R1_t xor R2_t xor S_t
        add_relation(out, [f"Z_{t}", f"S{15+t}", f"R1_{t}", f"R2_{t}", f"S{0+t}"])
        # оновлення FSM:
        # R1_{t+1} залежить від S_{13+t} і R2_t
        add_relation(out, [f"R1_{t+1}", f"S{13+t}", f"R2_{t}"])
        # R2_{t+1} отримуємо з R1_t
        add_relation(out, [f"R2_{t+1}", f"R1_{t}"])
        # оновлення LFSR:
        # новий стан S_{t+16} залежить від S_t, S_{t+11} та S_{t+13}
        add_relation(out, [f"S{t+16}", f"S{t}", f"S{t+11}", f"S{t+13}"])
    out.write("known\n")
    for t in range(ROUNDS):
        out.write(f"Z_{t}\n")
    out.write("end\n")

print("relations.txt generated")
#для запуску Autoguess треба скачати бібліотеку (pip install "autoguess[smt]")
#далі запустити сам autoguess (autoguess -i relations.txt -mg 7 -ms 50 -s smt -smts z3 --nograph) -> один з результатів output file