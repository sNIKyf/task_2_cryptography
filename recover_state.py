from strumok import Strumok

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


def simulate_attack(initial_state):
    state = dict(initial_state)
    changed = True

    def put(name, value):
        nonlocal changed
        if name not in state:
            state[name] = value
            changed = True

    while changed:
        changed = False
        # 1. Зв'язки R2 -> R1
        if "R2_3" in state: put("R1_2", R1[2])
        if "R2_8" in state: put("R1_7", R1[7])
        if "R2_10" in state: put("R1_9", R1[9])
        # 2. Зв'язки R1, S -> R2, S
        if "R1_7" in state and "S19" in state: put("R2_6", R2[6])
        if "R1_9" in state and "R2_8" in state: put("S21", S[21])
        if "R2_6" in state: put("R1_5", R1[5])
        # 3. Рівняння виходу
        if all(x in state for x in ["Z_6", "S21", "R2_6", "S6"]): put("R1_6", R1[6])
        if "R1_6" in state: put("R2_7", R2[7])
        if all(x in state for x in ["Z_7", "R1_7", "R2_7", "S7"]): put("S22", S[22])
        # 4. Рекурента LFSR
        if all(x in state for x in ["S22", "S6", "S19"]): put("S17", S[17])
        if all(x in state for x in ["R1_5", "S17"]): put("R2_4", R2[4])
        if "R2_4" in state: put("R1_3", R1[3])
        if all(x in state for x in ["Z_3", "R1_3", "R2_3", "S3"]): put("S18", S[18])
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
