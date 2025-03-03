import matplotlib.pyplot as plt
import numpy as np

# Chemin du fichier contenant les données
file_path = "/usr/vm/dump_percentage.txt"

# Listes pour stocker les temps et les pourcentages des 4 ensembles de données
times_1 = [0]  # Ajout du point (0, 0)
percentages_1 = [0]
times_2 = [0]
percentages_2 = [0]
times_3 = [0]
percentages_3 = [0]
times_4 = [0]
percentages_4 = [0]

# Lecture du fichier
with open(file_path, "r") as file:
    lines = file.readlines()

# Séparation des données en 4 ensembles
for i, line in enumerate(lines):
    time, percentage = line.strip().split()
    time = int(time)
    percentage = int(percentage)
    
    if i < 10:  # Les 10 premières lignes correspondent au premier ensemble
        times_1.append(time)
        percentages_1.append(percentage)
    elif i < 20:  # Les 10 lignes suivantes correspondent au deuxième ensemble
        times_2.append(time)
        percentages_2.append(percentage)
    elif i < 30:  # Les 10 lignes suivantes correspondent au troisième ensemble
        times_3.append(time)
        percentages_3.append(percentage)
    else:  # Les 10 lignes suivantes correspondent au quatrième ensemble
        times_4.append(time)
        percentages_4.append(percentage)

# Fonction pour transformer les temps en échelle logarithmique personnalisée
def custom_log_scale(times):
    return np.log10(np.array(times) + 1)  # log10(x + 1) pour éviter log(0)

# Transformation des temps en échelle logarithmique personnalisée
times_1_transformed = custom_log_scale(times_1)
times_2_transformed = custom_log_scale(times_2)
times_3_transformed = custom_log_scale(times_3)
times_4_transformed = custom_log_scale(times_4)

# Tracé des 4 courbes
plt.figure(figsize=(12, 8))  # Taille de la figure

# Première courbe (SSD sans perturbation)
plt.plot(percentages_1, times_1_transformed, marker='o', linestyle='-', color='b', label="Dump without perturbation SSD")

# Deuxième courbe (SSD avec perturbation)
plt.plot(percentages_2, times_2_transformed, marker='s', linestyle='--', color='r', label="Dump with perturbation SSD")

# Troisième courbe (HDD sans perturbation)
plt.plot(percentages_3, times_3_transformed, marker='^', linestyle='-.', color='g', label="Dump without perturbation HDD")

# Quatrième courbe (HDD avec perturbation)
plt.plot(percentages_4, times_4_transformed, marker='D', linestyle=':', color='m', label="Dump with perturbation HDD")

# Ajout du point (0, 0) pour toutes les courbes
plt.plot(custom_log_scale([0])[0], 0, marker='o', color='black', linestyle='None', label="Starting point (0, 0)")

# Configuration de l'axe des abscisses
plt.yticks(
    custom_log_scale([0, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]),  # Points personnalisés
    labels=["0", "10", "20", "50", "100", "200", "500", "1000", "2000", "5000", "10000"]  # Étiquettes
)

# Ajout des labels et du titre
plt.ylabel("Elapsed time (seconds) - Custom log scale")
plt.xlabel("Percentage of data dumped (%)")
plt.title("Comparison of Redis dump times with custom log scale (SSD and HDD)")

# Ajout d'une grille pour une meilleure lisibilité
plt.grid(True, which="both", ls="--")

# Affichage de la légende
plt.legend()

# Enregistrement du graphique dans un fichier
plt.savefig("dump_comparison_custom_log_scale.png")

# Affichage de la courbe
plt.show()