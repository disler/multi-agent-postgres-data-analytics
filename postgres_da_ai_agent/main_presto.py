import tkinter as tk

class Counter:
    def __init__(self, master):
        self.master = master
        self.count = 0
        self.button = tk.Button(master, text="Count: 0", command=self.increment)
        self.button.pack()

    def increment(self):
        if self.count < 10:
            self.count += 1
            self.button.config(text=f"Count: {self.count}")
        if self.count == 10:
            self.button.config(state="disabled")

def main():
    root = tk.Tk()
    counter = Counter(root)
    root.mainloop()

if __name__ == "__main__":
    main()
