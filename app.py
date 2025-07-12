import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ea_processor import generate_eas


class EAApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Enumeration Area Generator")

        # Input paths
        self.admin_path = tk.StringVar()
        self.pop_path = tk.StringVar()
        self.roads_path = tk.StringVar()
        self.rivers_path = tk.StringVar()
        self.settlements_path = tk.StringVar()

        # Parameters
        self.max_pop = tk.IntVar(value=750)
        self.max_area = tk.DoubleVar(value=9.0)

        self.create_widgets()

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(padx=10, pady=10)

        # Admin Boundary
        tk.Label(frame, text="Admin Boundary (Shapefile):").grid(row=0, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.admin_path, width=50).grid(row=0, column=1)
        tk.Button(frame, text="Browse", command=lambda: self.select_file(self.admin_path)).grid(row=0, column=2)

        # Population Raster
        tk.Label(frame, text="Population Raster (GeoTIFF):").grid(row=1, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.pop_path, width=50).grid(row=1, column=1)
        tk.Button(frame, text="Browse", command=lambda: self.select_file(self.pop_path)).grid(row=1, column=2)

        # Optional Files
        tk.Label(frame, text="Optional Layers:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky='w')

        tk.Label(frame, text="Roads (Shapefile):").grid(row=3, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.roads_path, width=50).grid(row=3, column=1)
        tk.Button(frame, text="Browse", command=lambda: self.select_file(self.roads_path)).grid(row=3, column=2)

        tk.Label(frame, text="Rivers (Shapefile):").grid(row=4, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.rivers_path, width=50).grid(row=4, column=1)
        tk.Button(frame, text="Browse", command=lambda: self.select_file(self.rivers_path)).grid(row=4, column=2)

        tk.Label(frame, text="Settlements (Shapefile):").grid(row=5, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.settlements_path, width=50).grid(row=5, column=1)
        tk.Button(frame, text="Browse", command=lambda: self.select_file(self.settlements_path)).grid(row=5, column=2)

        # Parameters
        tk.Label(frame, text="Constraints:", font=("Arial", 10, "bold")).grid(row=6, column=0, sticky='w')

        tk.Label(frame, text="Max Population per EA:").grid(row=7, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.max_pop).grid(row=7, column=1)

        tk.Label(frame, text="Max Area per EA (km²):").grid(row=8, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.max_area).grid(row=8, column=1)

        # Run Button
        tk.Button(frame, text="Generate EAs", command=self.run_analysis).grid(row=9, column=1, pady=10)

        # Plot area
        self.figure = plt.Figure(figsize=(8, 6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def select_file(self, var):
        path = filedialog.askopenfilename(
            filetypes=[("All Files", "*.*"), ("Shapefile", "*.shp"), ("GeoTIFF", "*.tif")]
        )
        if path:
            var.set(path)

    def run_analysis(self):
        try:
            self.ax.clear()

            eas_gdf = generate_eas(
                self.admin_path.get(),
                self.pop_path.get(),
                max_pop=self.max_pop.get(),
                max_area=self.max_area.get(),
                roads_path=self.roads_path.get() or None,
                rivers_path=self.rivers_path.get() or None,
                settlements_path=self.settlements_path.get() or None
            )

            eas_gdf.plot(ax=self.ax, column='population', legend=True, cmap='OrRd', edgecolor='black')
            self.ax.set_title("Generated Enumeration Areas")
            self.canvas.draw()

            # Save output
            output_path = "output/eas.shp"
            os.makedirs("output", exist_ok=True)
            eas_gdf.to_file(output_path)
            messagebox.showinfo("Success", f"EAs saved to {output_path}")

        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = EAApp(root)
    root.mainloop()
