def active_helper(x, y):
    return x + y

def unused_old_function(a, b):
    print("This is legacy unused code")
    c = a * b
    return c

class ActiveClass:
    def process(self):
        return active_helper(10, 20)

class UnusedLegacyClass:
    def do_nothing(self):
        pass
