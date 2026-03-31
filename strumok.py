from strumok_tables import *
import time

class Strumok:
    MASK_64 = 0xFFFFFFFFFFFFFFFF

    def __init__(self):
        # LFSR state: 16 registers (s0 to s15) 
        self.s = [0] * 16
        # FSM state: 2 registers (r1, r2) 
        self.r1 = 0
        self.r2 = 0

# the ability to set the internal state directly.
    def set_state(self, s_list, r1, r2):
        if len(s_list) != 16:
            raise ValueError("LFSR state must consist of 16 words.")
        self.s = [val & self.MASK_64 for val in s_list]
        self.r1 = r1 & self.MASK_64
        self.r2 = r2 & self.MASK_64

# non linear transformation using strumok_tables
    def substitute_T(self, v):
        return (
            strumok_T0[v & 0xFF] ^
            strumok_T1[(v >> 8) & 0xFF] ^
            strumok_T2[(v >> 16) & 0xFF] ^
            strumok_T3[(v >> 24) & 0xFF] ^
            strumok_T4[(v >> 32) & 0xFF] ^
            strumok_T5[(v >> 40) & 0xFF] ^
            strumok_T6[(v >> 48) & 0xFF] ^
            strumok_T7[(v >> 56) & 0xFF]
        )

# multiplication by alpha table
    def multiply_alpha(self, v):
        top_byte = (v >> 56) & 0xFF
        shifted = (v << 8) & self.MASK_64
        return shifted ^ strumok_alpha_mul[top_byte]

# multiplication by alpha inverse table
    def multiply_alpha_inv(self, v):
        bottom_byte = v & 0xFF
        shifted = (v >> 8) & self.MASK_64
        return shifted ^ strumok_alphainv_mul[bottom_byte]

# the main step function that updates the state and produces output
    def step(self, mode="NORMAL"):
        # FSM output calculation
        F = ((self.s[15] + self.r1) & self.MASK_64) ^ self.r2
        gamma = F ^ self.s[0]

        # prepare next FSM state
        r1_next = (self.s[13] + self.r2) & self.MASK_64
        r2_next = self.substitute_T(self.r1)

        # LFSR feedback 
        feedback = self.multiply_alpha(self.s[0]) ^ \
                   self.multiply_alpha_inv(self.s[11]) ^ \
                   self.s[13]

        if mode == "INIT":
            feedback ^= F

        # state update
        self.r1 = r1_next
        self.r2 = r2_next
        self.s.pop(0)
        self.s.append(feedback & self.MASK_64)

        return gamma
# initialization function that sets up the state based on key and IV, and performs warm-up cycles
    def initialize(self, key_words, iv_words):
        self.r1 = 0
        self.r2 = 0
        K = key_words
        IV = iv_words

        if len(K) == 4:
            self.s[15], self.s[14], self.s[13], self.s[12] = ~K[0],  K[1], ~K[2],  K[3]
            self.s[11], self.s[10], self.s[9],  self.s[8]  =  K[0], ~K[1],  K[2],  K[3]
            self.s[7],  self.s[6],  self.s[5],  self.s[4]  = ~K[0], ~K[1],  K[2]^IV[3], K[3]
            self.s[3],  self.s[2],  self.s[1],  self.s[0]  =  K[0]^IV[2], K[1]^IV[1], K[2], K[3]^IV[0]
        elif len(K) == 8:
            self.s[15], self.s[14], self.s[13], self.s[12] =  K[0], ~K[1],  K[2],  K[3]
            self.s[11], self.s[10], self.s[9],  self.s[8]  = ~K[7],  K[5], ~K[6],  K[4]^IV[3]
            self.s[7],  self.s[6],  self.s[5],  self.s[4]  = ~K[0],  K[1],  K[2]^IV[2], K[3]
            self.s[3],  self.s[2],  self.s[1],  self.s[0]  =  K[4]^IV[1], K[5], K[6],  K[7]^IV[0]
        else:
            raise ValueError("Key must be 256 or 512 bits (4 or 8 words).")

        self.s = [word & self.MASK_64 for word in self.s]

        # 32 warm-up cycles
        for _ in range(32):
            self.step(mode="INIT")

        # final transition cycle 
        self.step(mode="NORMAL")

# generate keystream words
    def generate_keystream(self, num_words):
        return [self.step() for _ in range(num_words)]

# verefication and speed check
def verify_and_benchmark():
    tests = [
        {
            "name": "Strumok-256 test vector 1",
            "key": [0x0000000000000000, 
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x8000000000000000],
            "iv": [0x0000000000000000, 
                   0x0000000000000000, 
                   0x0000000000000000, 
                   0x0000000000000000],
            "expected_z0": 0xe442d15345dc66ca
        },
        {
            "name": "Strumok-256 test vector 2",
            "key": [0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa],
            "iv": [0x0000000000000000, 
                   0x0000000000000000, 
                   0x0000000000000000, 
                   0x0000000000000000],
            "expected_z0": 0xa7510b38c7a95d1d
        },
        {
            "name": "Strumok-256 test vector 3",
            "key": [0x0000000000000000, 
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x8000000000000000],
            "iv": [0x0000000000000001, 
                   0x0000000000000002, 
                   0x0000000000000003, 
                   0x0000000000000004],
            "expected_z0": 0xfe44a2508b5a2acd
        },
        {
            "name": "Strumok-256 test vector 4",
            "key": [0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa],
            "iv": [0x0000000000000001, 
                   0x0000000000000002, 
                   0x0000000000000003, 
                   0x0000000000000004],
            "expected_z0": 0xe6d0efd9cea5abcd
        },
        {
            "name": "Strumok-512 test vector 1",
            "key": [0x0000000000000000,
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x8000000000000000],
            "iv": [0x0000000000000000, 
                   0x0000000000000000, 
                   0x0000000000000000, 
                   0x0000000000000000],
            "expected_z0": 0xf5b9ab51100f8317
        },
        {
            "name": "Strumok-512 test vector 2",
            "key": [0xaaaaaaaaaaaaaaaa,
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa],
            "iv": [0x0000000000000000, 
                   0x0000000000000000, 
                   0x0000000000000000, 
                   0x0000000000000000],
            "expected_z0": 0xd2a6103c50bd4e04
        },
        {
            "name": "Strumok-512 test vector 3",
            "key": [0x0000000000000000,
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x0000000000000000, 
                    0x8000000000000000],
            "iv": [0x0000000000000001, 
                   0x0000000000000002, 
                   0x0000000000000003, 
                   0x0000000000000004],
            "expected_z0": 0xcca12eae8133aaaa
        },
        {
            "name": "Strumok-512 test vector 4",
            "key": [0xaaaaaaaaaaaaaaaa,
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa, 
                    0xaaaaaaaaaaaaaaaa],
            "iv": [0x0000000000000001, 
                   0x0000000000000002, 
                   0x0000000000000003, 
                   0x0000000000000004],
            "expected_z0": 0x965648e775c717d5
        }
    ]

    print(f"{'Algorithm':<25} | {'Status':<10} | {'Max Speed (Mbps)':<15}")
    print("-" * 60)

    for case in tests:
        cipher = Strumok()
        cipher.initialize(case["key"], case["iv"])
        
        # correctness verification 
        gamma = cipher.generate_keystream(1)
        status = "PASS" if gamma[0] == case["expected_z0"] else "FAIL"
        
        # speed estimation 
        sample_size = 500_000
        start = time.perf_counter()
        _ = cipher.generate_keystream(sample_size)
        duration = time.perf_counter() - start
        mbps = (sample_size * 64 / 1e6) / duration
        
        print(f"{case['name']:<25} | {status:<10} | {mbps:>16.2f}")

if __name__ == "__main__":
    verify_and_benchmark()