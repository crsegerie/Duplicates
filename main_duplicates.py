from duplicates import *
import pandas as pd

""" step 0 : vérifier qu'il ne manque pas des codes postaux et qu'ils soient bien formatés """

# VARIABLES
df = pd.read_excel('distributeurs_merge.xlsx',
                   sep=';', encoding='utf-8', converters={'code_postal': str, "code_ape": str, "tag": str, "identifiant": str, "identifiant_local": str})

folder = "results"  # Nom du fichier dans lequel on enregistre les résultats finaux
columns_merge = ['nom_etablissement', 'adresse']  # Nom des colonnes sur lesquelles on calcule les jointures
nbr_frequent_words = 20  # Nombre de mots qui reviennent tellement souvent qu'ils seront pas considérés
additional_columns_in_check = ['identifiant', "telephone"]  # Si dans l'excel intermédiaires de check, on veut rajouter des colonne pour être sûr de l'endroit où l'on met les croix

step = 1

# step 1 : Calibrate the number of frequent words you want to use
# step 2 : create the folder consolidation_check.xlsx, you'll have then to put the crosses in consolidation_check.xlsx
# Step 3 : And finally you have to execute step 3 : and create


duplicates = Duplicates(folder)

if step == 1:
    print("Initialisation ...")
    common_words = duplicates.find_often_used_word(df, columns_merge=columns_merge, level=nbr_frequent_words)
    print("List of the frequently used word: ", common_words)

if step == 2:
    print("Lancement de l'étape 2")
    common_words = duplicates.find_often_used_word(df, columns_merge=columns_merge, level=nbr_frequent_words)
    print("List of the frequently used word: ", common_words)
    duplicates.create_check(df, columns_merge=columns_merge, additional_columns_in_check=additional_columns_in_check, common_words=common_words, TRESHOLD_INF=50, TRESHOLD_SUP=90)

if step == 3:
    print("Lancement de l'étape 3")
    df_manual = pd.read_excel('duplicates_check.xlsx', sep=';', encoding='utf-8', converters={'match_id': int, 'id_duplicates': int})
    duplicates.merge(df, df_manual, columns_merge=columns_merge, REFORMAT_POSTAL_CODE=False, source_priority={"2019, kompass": 1, "2019, nld_scrap_distribution": 0})
