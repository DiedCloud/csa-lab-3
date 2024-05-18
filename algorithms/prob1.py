def classic(limit):
    total = 0
    for number in range(limit):
        if number % 3 == 0 or number % 5 == 0:
            total += number
    return total

def classic_without_mod(limit):
    total = 0
    mod3 = 0
    mod5 = 0
    for number in range(limit):
        if mod3 == 0 or mod5 == 0:
            total += number
        mod3 += 1
        if mod3 == 3:
            mod3 = 0
        mod5 += 1
        if mod5 == 5:
            mod5 = 0
    return total


if __name__ == "__main__":
    lim = 1000
    assert classic(lim) == classic_without_mod(lim)