from copy import deepcopy as DC


class Test:
    def __init__(self, dict):
        self.dict = DC(dict)


d1 = {
    "a": 1,
    "b": {"c": 3, "d": 4}
}


t1 = Test(d1)

print("Init state.")
print("d1 ", d1)
print("t1 ", t1.dict)

print("######")

d1["a"] = 22
d1["b"]["d"] = 25
print("Changed d1.")
print("d1 ", d1)
print("t1 ", t1.dict)

t1.dict["a"] = 321
t1.dict["b"]["c"] = 312
print("Changed t1.")
print("d1 ", d1)
print("t1 ", t1.dict)

# !! Python constructor does NOT use deepcopy.
# Implement manually.
