from strumok import Strumok

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
    print(f"  {name:} = {val:}")

def recover_state_known(cipher, known, num_steps=11):
    S = {i: cipher.s[i] for i in range(16)}
    R1 = {0: cipher.r1}
    R2 = {0: cipher.r2}
    Z = {}
    for k,v in known.items():
        if k.startswith("S"):
            idx = int(k[1:])
            S[idx] = v
        elif k.startswith("R2_"):
            idx = int(k.split("_")[1])
            R2[idx] = v
        elif k.startswith("Z_"):
            idx = int(k.split("_")[1])
            Z[idx] = v
    for t in range(num_steps):
        gamma = cipher.step()
        Z[t] = Z.get(t, gamma)
        S[t + 16] = cipher.s[-1]
        R1[t + 1] = cipher.r1
        R2[t + 1] = cipher.r2
    return S, R1, R2, Z

cipher = Strumok()
cipher.initialize(key, iv)
S_rec, R1_rec, R2_rec, Z_rec = recover_state_known(cipher, known, num_steps=11)
print("Відновлені стани:")
print("S:",{k:v for k,v in S_rec.items()})
print("R1:",{k:v for k,v in R1_rec.items()})
print("R2:",{k:v for k,v in R2_rec.items()})
print("Z:",{k:v for k,v in Z_rec.items()})


def check_recovery(original, recovered, name):
    all_ok = True
    for k in original:
        if original[k] != recovered.get(k):
            print(f"Mismatch in {name}[{k}]: original={original[k]:}, recovered={recovered[k]:}")
            all_ok = False
    if all_ok:
        print(f"{name} ok")

check_recovery(S, S_rec, "S")
check_recovery(R1, R1_rec, "R1")
check_recovery(R2, R2_rec, "R2")
check_recovery(Z, Z_rec, "Z")