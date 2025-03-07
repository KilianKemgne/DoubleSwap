import matplotlib.pyplot as plt

# Chemin du fichier contenant les données
file_path = "/usr/vm/dump_percentage.txt"

# Listes pour stocker les temps et les pourcentages des deux ensembles de données
times_1 = []
percentages_1 = []
times_2 = []
percentages_2 = []

# Lecture du fichier
with open(file_path, "r") as file:
    lines = file.readlines()

# Séparation des données en deux ensembles
for i, line in enumerate(lines):
    time, percentage = line.strip().split()
    if i < 10:  # Les 10 premières lignes correspondent au premier ensemble
        times_1.append(int(time))
        percentages_1.append(int(percentage))
    else:  # Les 10 lignes suivantes correspondent au deuxième ensemble
        times_2.append(int(time))
        percentages_2.append(int(percentage))

# Tracé des deux courbes
plt.figure(figsize=(10, 6))  # Taille de la figure

# Première courbe (Dump sans perturbateur)
plt.plot(times_1, percentages_1, marker='o', linestyle='-', color='b', label="Dump without perturbation")

# Deuxième courbe (Dump avec perturbateur)
plt.plot(times_2, percentages_2, marker='s', linestyle='--', color='r', label="Dump with perturbation")

# Ajout des labels et du titre
plt.xlabel("Elapsed time (seconds)")
plt.ylabel("Percentage of data dumped (%)")
plt.title("Comparison of Redis dump times with and without perturbation")

# Ajout d'une grille pour une meilleure lisibilité
plt.grid(True)

# Affichage de la légende
plt.legend()

# Enregistrement du graphique dans un fichier
plt.savefig("dump_comparison.png")

# Affichage de la courbe
plt.show()