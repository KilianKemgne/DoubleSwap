import memcache
import sys
import time

# Configuration
MEMCACHED_SERVER = 'localhost:11211'
DATA_SIZE = 1 * 1024 * 1024  # 1 Mo de données par clé
TARGET_SIZE = 6 * 1024 * 1024 * 1024  # 6 Go en octets

# Connexion à Memcached
client = memcache.Client([MEMCACHED_SERVER], debug=0)

# Fonction pour générer une valeur unique
def generate_unique_value():
    # Récupère l'heure actuelle en nanosecondes
    nanoseconds = int(time.time() * 1e9)
    # Convertit en chaîne de caractères
    unique_value = str(nanoseconds)
    # Complète avec des zéros pour atteindre la taille souhaitée
    unique_value = unique_value.ljust(DATA_SIZE, '0')
    return unique_value[:DATA_SIZE]  # Tronque à la taille exacte

# Fonction pour vérifier qu'une clé existe et que sa valeur est correcte
def verify_key(key, expected_value):
    stored_value = client.get(key)
    if stored_value is None:
        print(f"Erreur : La clé {key} n'existe pas dans Memcached.")
        print(f"Valeur attendue : {expected_value}")
        return False
    elif stored_value != expected_value:
        print(f"Erreur : La valeur de la clé {key} ne correspond pas à la valeur attendue.")
        print(f"Valeur stockée : {stored_value}")
        print(f"Valeur attendue : {expected_value}")
        return False
    else:
        print(f"Succès : La clé {key} a été vérifiée et sa valeur est correcte.")
        return True

# Fonction pour injecter des données
def inject_data():
    total_size = 0
    key_counter = 0

    while total_size < TARGET_SIZE:
        key = f'key_{key_counter}'
        value = generate_unique_value()  # Génère une valeur unique

        # Stocker la valeur dans Memcached
        success = client.set(key, value)
        if not success:
            print(f"Erreur : Impossible de stocker la clé {key} dans Memcached.")
            sys.exit(1)

        # Vérifier immédiatement que la valeur a bien été stockée
        if not verify_key(key, value):
            print("Arrêt du script en raison d'une erreur de vérification.")
            sys.exit(1)

        # Mettre à jour la taille totale
        total_size += DATA_SIZE
        key_counter += 1

        # Afficher la progression
        progress = (total_size / TARGET_SIZE) * 100
        print(f"Injected {total_size / (1024 * 1024):.2f} MB / {TARGET_SIZE / (1024 * 1024 * 1024):.2f} GB ({progress:.2f}%)")

    print("Injection terminée. 6 Go de données ont été injectés dans Memcached.")

# Exécution du script
if __name__ == '__main__':
    try:
        inject_data()
    except KeyboardInterrupt:
        print("\nInjection interrompue par l'utilisateur.")
        sys.exit(0)
