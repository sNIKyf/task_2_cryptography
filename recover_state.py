from strumok import Strumok
from strumok_tables import *
# Зберігаємо всі значення S, R1, R2 та виходи Z для перших 11 кроків.
# Вони потрібні лише для перевірки й для отримання деяких векторів для атаки.
def get_trajectory(key_words, iv_words, num_steps=11):
    cipher = Strumok()
    cipher.initialize(key_words, iv_words)
    S  = {}
    R1 = {}
    R2 = {}
    Z  = {}
    for i in range(16):
        S[i] = cipher.s[i]
    R1[0] = cipher.r1
    R2[0] = cipher.r2
    for t in range(num_steps):
        gamma = cipher.step()
        Z[t] = gamma
        S[t + 16] = cipher.s[-1]
        R1[t + 1] = cipher.r1
        R2[t + 1] = cipher.r2
    return S, R1, R2, Z
#приклад значень ключа й iv взято з ДСТУ 8845-2019 - Алгоритм симетричного потокового перетворення (Струмок) - 2019.pdf
key = [
    0x0000000000000000,
    0x0000000000000000,
    0x0000000000000000,
    0x8000000000000000
]

iv = [
    0x0000000000000000,
    0x0000000000000000,
    0x0000000000000000,
    0x0000000000000000
]

S, R1, R2, Z = get_trajectory(key, iv, num_steps=11)
# Тут ми імітуємо результат AutoGuess:
# припускаємо, що нападник уже "вгадав" 7 базисних змінних і знає 11 вихідних слів Z_0 ... Z_10.
known = {
    "S3":S[3],
    "S6":S[6],
    "S7":S[7],
    "S19":S[19],
    "R2_3":R2[3],
    "R2_8":R2[8],
    "R2_10":R2[10],
    "Z_0":Z[0],"Z_1":Z[1],"Z_2":Z[2],
    "Z_3":Z[3],"Z_4":Z[4],"Z_5":Z[5],
    "Z_6":Z[6],"Z_7":Z[7],"Z_8":Z[8],
    "Z_9":Z[9],"Z_10":Z[10],
}

print("Реальні значення для атаки:")
for name, val in known.items():
    print(f"  {name:} = {hex(val):}")


MASK = 0xffffffffffffffff

def substitute_T(v):
    return (
        strumok_T0[v & 0xff] ^
        strumok_T1[(v >> 8) & 0xff] ^
        strumok_T2[(v >> 16) & 0xff] ^
        strumok_T3[(v >> 24) & 0xff] ^
        strumok_T4[(v >> 32) & 0xff] ^
        strumok_T5[(v >> 40) & 0xff] ^
        strumok_T6[(v >> 48) & 0xff] ^
        strumok_T7[(v >> 56) & 0xff]
    )

def simulate_attack(initial_state):
    state = dict(initial_state)
    changed = True

    def put(name, value):
        nonlocal changed
        if name not in state:
            state[name] = value & MASK
            changed = True

    while changed:
        changed = False
        # R2_{t+1} = T(R1_t)  →  звідси НЕ можна отримати R1_t без T^{-1}.
        # Тому ці кроки пропускаємо, вони виконані "вгадуванням" R2_3, R2_8, R2_10.
        # Натомість використовуємо R1_{t+1} = S_{t+13} + R2_t:
        # R1_7 = S_19 + R2_6  →  але R2_6 ще невідома; пізніше
        # R2_6 = R1_7 - S_19  →  якщо R1_7 відома... теж поки ні.
        # Єдиний вихід — через рівняння виходу:
        # Z_6 = ((S_21 + R1_6) ^ R2_6) ^ S_6
        # Кроки де T^{-1} потрібна (State 0 в Autoguess)
        # R2_3 = T(R1_2)  →  R1_2 = T^{-1}(R2_3)
        # Для демонстрації: перевіряємо і використовуємо реальне R1_2, але явно верифікуємо через T
        if "R2_3" in state and "R1_2" not in state:
            # В реальній атаці: розв'язок системи 64x64 лін. рівнянь над GF(2)
            # Для демонстрації: підбираємо R1_2 і перевіряємо T(R1_2) == R2_3
            r1_2_candidate = R1[2]  # уявляємо що отримано через T^{-1}
            assert substitute_T(r1_2_candidate) == state["R2_3"]
            put("R1_2", r1_2_candidate)

        if "R2_8" in state and "R1_7" not in state:
            r1_7_candidate = R1[7]
            assert substitute_T(r1_7_candidate) == state["R2_8"]
            put("R1_7", r1_7_candidate)

        if "R2_10" in state and "R1_9" not in state:
            r1_9_candidate = R1[9]
            assert substitute_T(r1_9_candidate) == state["R2_10"]
            put("R1_9", r1_9_candidate)

        # R1_{t+1} = S_{t+13} + R2_t  →  R2_6 = R1_7 - S_19
        if "R1_7" in state and "S19" in state:
            put("R2_6", (state["R1_7"] - state["S19"]) & MASK)

        # R1_9 = S_21 + R2_8  →  S_21 = R1_9 - R2_8
        if "R1_9" in state and "R2_8" in state:
            put("S21", (state["R1_9"] - state["R2_8"]) & MASK)

        # R2_6 = T(R1_5)  →  R1_5 через T^{-1} (аналогічно)
        if "R2_6" in state and "R1_5" not in state:
            r1_5_candidate = R1[5]
            assert substitute_T(r1_5_candidate) == state["R2_6"]
            put("R1_5", r1_5_candidate)

        # Z_6 = ((S_21 + R1_6) ^ R2_6) ^ S_6  →  R1_6
        if all(x in state for x in ["Z_6", "S21", "R2_6", "S6"]):
            inner = (state["Z_6"] ^ state["S6"]) ^ state["R2_6"]
            put("R1_6", (inner - state["S21"]) & MASK)

        # R2_7 = T(R1_6)  →  пряме обчислення!
        if "R1_6" in state:
            put("R2_7", substitute_T(state["R1_6"]))

        # Z_7 = ((S_22 + R1_7) ^ R2_7) ^ S_7  →  S_22
        if all(x in state for x in ["Z_7", "R1_7", "R2_7", "S7"]):
            inner = (state["Z_7"] ^ state["S7"]) ^ state["R2_7"]
            put("S22", (inner - state["R1_7"]) & MASK)

        # S_22 = alpha*S_6 ^ alpha^{-1}*S_17 ^ S_19  →  S_17
        if all(x in state for x in ["S22", "S6", "S19"]):
            cipher = Strumok()
            rhs = state["S22"] ^ cipher.multiply_alpha(state["S6"]) ^ state["S19"]
            put("S17", cipher.multiply_alpha(rhs))

        # R1_5 = S_17 + R2_4  →  R2_4
        if "R1_5" in state and "S17" in state:
            put("R2_4", (state["R1_5"] - state["S17"]) & MASK)

        # R2_4 = T(R1_3)  →  T^{-1}
        if "R2_4" in state and "R1_3" not in state:
            r1_3_candidate = R1[3]
            assert substitute_T(r1_3_candidate) == state["R2_4"], "T(R1_3) ≠ R2_4!"
            put("R1_3", r1_3_candidate)

        # Z_3 = ((S_18 + R1_3) ^ R2_3) ^ S_3  →  S_18
        if all(x in state for x in ["Z_3", "R1_3", "R2_3", "S3"]):
            inner = (state["Z_3"] ^ state["S3"]) ^ state["R2_3"]
            put("S18", (inner - state["R1_3"]) & MASK)

    return state

recovered = simulate_attack(known)

print("\nВідновлені значення:")
for k in sorted(recovered):
    if k not in known:
        print(f"{k}: {hex(recovered[k])}")

print("\nПеревіряємо результати")
errors = 0
for key, val in recovered.items():
    ref_val = None
    if key.startswith("S"):
        ref_val = S[int(key[1:])]
    elif key.startswith("R1_"):
        ref_val = R1[int(key[3:])]
    elif key.startswith("R2_"):
        ref_val = R2[int(key[3:])]
    elif key.startswith("Z_"):
        ref_val = Z[int(key[2:])]
    if ref_val is not None and val != ref_val:
        print(f"Помилка у {key}: очікували {ref_val:}, отримали {val:}")
        errors += 1
if errors == 0:
    print("ok")
else:
    print(f"Знайдено помилок:{errors}")

#otput запуску кода:
# Реальні значення для атаки:
#   S3 = 0x87cdfeb2e4c6cfe1
#   S6 = 0xf665a966754641fe
#   S7 = 0x004d0760ecf7166b
#   S19 = 0xad16a6e80e6925da
#   R2_3 = 0xfc31b029925b9230
#   R2_8 = 0xe99ce0e9a4e4bd3f
#   R2_10 = 0x3a6d5a6c75b9a9fb
#   Z_0 = 0xe442d15345dc66ca
#   Z_1 = 0xf47d700ecc66408a
#   Z_2 = 0xb4cb284b5477e641
#   Z_3 = 0xa2afc9092e4124b0
#   Z_4 = 0x728e5fa26b11a7d9
#   Z_5 = 0xe6a7b9288c68f972
#   Z_6 = 0x70eb3606de8ba44c
#   Z_7 = 0xaced7956bd3e3de7
#   Z_8 = 0x5af7ec2a83c7063e
#   Z_9 = 0x78b4b5fe3bae5e01
#   Z_10 = 0x6bfaebec04790b89
#
# Відновлені значення:
#   R1_2: 0xbba26de78b4dcb30
#   R1_3: 0x43287ccbaa09595c
#   R1_5: 0xf38f9ea74c3812e9
#   R1_6: 0xda80f86238e29e66
#   R1_7: 0x5f53ef4a6cbe2781
#   R1_9: 0x43cfbf8a619b02ee
#   R2_4: 0x85a8d686fbd7067
#   R2_6: 0xb23d48625e5501a7
#   R2_7: 0x5bd96958b45be284
#   S17: 0xeb35113edc7aa282
#   S18: 0x962b0ac6aed32005
#   S21: 0x5a32dea0bcb645af
#   S22: 0x9825282478d4a187
#
# Перевіряємо результати
# ok
