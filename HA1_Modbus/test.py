def ieee754_to_float_manual(bits: str) -> float:
    ####################### iee754 format ######################
    #  0             10000001          01110000000000000000000 
    # sign (1b)   exponent(8 bits)          mantissa (23 bits)
    ############################################################ 
    
    # Split fields
    sign_bit = bits[0]
    exp_bits = bits[1:9]
    mantissa_bits = bits[9:]

    # Convert sign
    sign = -1 if sign_bit == '1' else 1

    # Exponent (remove bias 127)
    exponent = int(exp_bits, 2) - 127

    # Mantissa reconstruction
    mantissa = 1.0
    for i, bit in enumerate(mantissa_bits, start=1):
        if bit == '1':
            mantissa += 2 ** (-i)

    # Final value
    val = sign * mantissa * (2 ** exponent)
    return val

bits = "01000000101110000000000000000000"  # 5.75
decoded = ieee754_to_float_manual(bits)
print(decoded)  # → 5.75