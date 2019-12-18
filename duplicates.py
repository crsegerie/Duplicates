import pandas as pd
from fuzzywuzzy import fuzz
import os


def strip_frequently_used_word(string, common_words):
    """delete from it all the common worlds"""
    for word in common_words:
        string = string.replace(word, '')
    return string


def intersection(lst1, lst2):
    """Calcule l'intersection entre deux listes"""
    # Use of hybrid method
    temp = set(lst2)
    lst3 = [value for value in lst1 if value in temp]
    return lst3


class Duplicates():
    """ Suppression of the duplicates contained in an Excel"""

    def __init__(self, output_folder="None"):
        """
        output_folder = "None" : The methods will just return the results without writting them on Excel
        output_folder = "Path" : The methods will return the results and writte them in the Path.
        """
        self.output_folder = output_folder

    def find_often_used_word(self, df, columns_merge=['nom_etablissement', 'adresse'], level=40):
        """return the list of the 40 most used words in the columns in columns_merge of df """
        dict = {}
        tab_digits = [str(i) for i in range(10)]
        for i, row in df.iterrows():
            for feature in columns_merge:
                elem = row[feature]
                if type(elem) == str:
                    elem = elem.lower()
                    tab_elem = elem.split(" ")
                    for x in tab_elem:
                        if x in dict.keys() and len(x) > 0 and x[0] not in tab_digits:
                            dict[x] += 1
                        else:
                            dict[x] = 0
        df_freq = pd.DataFrame()
        for x in dict.keys():
            if dict[x] > 2:
                d = {"nom": x, "frequence": dict[x]}
                df_freq = df_freq.append(d, ignore_index=True)
        df_freq = df_freq.sort_values('frequence', ascending=False)
        df_freq = df_freq.reset_index(drop=True)
        return list(df_freq.head(level)["nom"])

    def create_check(self, df, columns_merge=['nom_etablissement', 'adresse'], additional_columns_in_check=[], TRESHOLD_INF=50, TRESHOLD_SUP=90, common_words=[]):
        """
        Create consolidate_check.xlsx in which you have to put a cross per match
        ie : for triplet you put 3 crosses

        Inputs:
        An Excel containing a column 'code_postal' converted into a pandas DataFrame

        columns_merge : Name of the colums on which we will perform the merge
        Do not put in it the postal code
        There is still the possibility to put more than one feature in columns df_check
        However, if you put just the nom_etablissement in columns_merge, the algorithm will work nicely.
        We do not recommand putting in it the address

        Return :
        At the end, the algorithme will return an Excel in which the human-checker
        will have to put x in the column 'check'
        If the score is contained between the two tresholds, there is a manual check
        """

        # Think about the tests of conformity of the Excels : hypothesis : already done in Alteryx
        # Maybe a future improvement = count each word and delete the most frequent ones or ponderate by the inverse of their occurrence

        # Deleting perfect duplicates
        df.drop_duplicates(subset=columns_merge, keep='first', inplace=True)

        # Putting the index in the slicing in order to writting them down easily in the duplicates_check.xlsx
        df = df.reset_index(drop=True)
        df["id_duplicates"] = df.index.values

        # Uniformisation of the inputs, without changing the output of the final_duplicates.xlsx
        # That is not necessary but sometimes in the excels, code_postal is encoded as int or str
        for feature in columns_merge:
            df[feature] = df[feature].apply(str)

        # df which will be exported into Excel as consolidate_check
        df_check = pd.DataFrame()

        postal_codes = list(set(df['code_postal']))
        match_id = -1
        print("Analyzing the duplicates ...")
        for nbr_postal_code, postal_code in enumerate(postal_codes):
            # Une matrice par code postal

            print(nbr_postal_code, len(postal_codes))

            df_postal_code = df[df['code_postal'] == postal_code]

            # for each line in the short_excel, we seek the corresponding line in the long_excel
            for i, row_short in df_postal_code.iterrows():
                match_id += 1

                if len(df_postal_code) > 0:

                    # Contains all the lines of the long Excel which matches sufficiently with the line i of the shot Excel
                    df_match = pd.DataFrame()

                    for j, row_long in df_postal_code.iterrows():
                        if j > i:
                            # matching_score > TRESHOLD_SUP : very very probably a match
                            # matching_score between the two TRESHOLD : manual check
                            # matching_score < TRESHOLD_INF : very very unlikely to be a match

                            # We want to calculate the minimum between the matching score of the address and of the name
                            min_score = 100
                            for elem_merge in columns_merge:
                                str_long = row_long[elem_merge].lower()
                                str_short = row_short[elem_merge].lower()

                                # We delete the frequent words to also perform the duplicates check on it
                                str_long_without = strip_frequently_used_word(str_long, common_words)
                                str_short_without = strip_frequently_used_word(str_short, common_words)
                                score_without = fuzz.token_set_ratio(str_long_without, str_short_without)
                                score_with = fuzz.token_set_ratio(str_long, str_short)

                                # We want to find all the duplicates, so we take the maximum between score_without and score_with
                                score = max(score_with, score_without)
                                if score > TRESHOLD_INF:
                                    # min_score = min(matching_score(address), matching_score(name))
                                    if score < min_score:
                                        min_score = score
                                else:
                                    min_score = score
                                    # We break because the min_score = min(matching_score(address), matching_score(name))
                                    # and here we already now that eiher the two address or the two name are suffisciently different in order to not compare the other features
                                    break

                            # We copy the line in the df_match if the lines matches sufficiently
                            if min_score > TRESHOLD_INF:
                                row_long['match_id'] = match_id
                                row_long['source_duplicates'] = 'long'
                                row_long['first_line_match_id'] = 0
                                row_long['matching_score'] = min_score

                                df_match = df_match.append(row_long, sort=False)

                    # We print the potential best candidates after printing the short line
                    row_short['match_id'] = match_id
                    row_short['first_line_match_id'] = 1

                    if len(df_match) == 0:
                        # If no potential match have been found, we just write down the short single line
                        row_short['source_duplicates'] = 'single'
                        df_check = df_check.append(row_short, sort=False)
                    else:
                        # We sort the matches by putting the best matches first
                        df_match = df_match[df_match['matching_score'] > TRESHOLD_INF]
                        df_match = df_match.sort_values(by=['matching_score'], ascending=False)
                        df_match_max = df_match[df_match['matching_score'] == max(df_match['matching_score'])]
                        df_match_max = df_match_max.reset_index(drop=True)

                        if df_match_max.loc[0, 'matching_score'] > TRESHOLD_SUP:
                            # if the score of the best matches is high enough, thery are duplicates
                            if len(df_match_max) == 1:
                                row_short['source_duplicates'] = 'automatically merged'
                                df_match_max['source_duplicates'] = 'automatically merged'
                                row_short['check'] = 'x'
                                df_match_max.loc[0, 'check'] = 'x'
                            else:
                                # if there is a triplet having the same matching score, we let the human checker select the duplicates
                                row_short['source_duplicates'] = 'not merged because equality'
                                df_match_max['source_duplicates'] = 'not merged because equality'
                            df_check = df_check.append(row_short, sort=False)
                            df_check = df_check.append(df_match_max, sort=False)

                            #  à chaque fois qu'on fait un append comme df_check = df_check.append(df_match_max, sort=False), le code est beaucoup ralenti car l'append recopie tout le df_check. Ce problème a été patché dans la consolidation. On pourra s'en inspirer ici si besoin
                        else:
                            # if all matching score are under TRESHOLD_SUP, we writte down all matches
                            row_short['source_duplicates'] = 'manual check'
                            row_short['check'] = ''
                            df_match['source_duplicates'] = 'manual check'
                            df_check = df_check.append(row_short, sort=False)
                            df_check = df_check.append(df_match, sort=False)

                else:
                    print("No ", postal_code, "fund in the long Excel file.")

        # Keeping only the merge columns
        df_check = df_check[columns_merge + additional_columns_in_check + ['code_postal', 'match_id', "first_line_match_id", 'matching_score', 'source_duplicates', 'id_duplicates', "check"]]
        if self.output_folder != "None":
            df_check.to_excel("duplicates_check.xlsx", index=False,
                              encoding='utf-8', engine='xlsxwriter')
            print("Done")
        else:
            return df_check

    def merge(self, df, df_manual, columns_merge, REFORMAT_POSTAL_CODE=False, source_priority={}):
        """ Return the Excel without duplicates after having interpreted the duplicates_check.xlsx where the human checker had put the crosses
        Contrary to a previous version, here there is no need to declare a priority in order to perform the merge

        Inputs:
        An Excels file converted in Pandas DataFrame which contains duplicates
        - df
        And an Excel converted in Pandas DataFrame in which there are some crosses indicating the matches :
        - df_manual

        exemple of source_priority
        source_priority = {"source1": 1, "source2": 2, "source3": 3}
        > Here the source 3 has the highest priority, so if there is a conflict, we'll keep the data comming from 3

        Return :
        At the end, the algorithme will return in the results folder:
        - without_duplicates : df without_duplicates
        """
        pd.options.mode.chained_assignment = None  # default='warn'
        # Deleting perfect duplicates
        df.drop_duplicates(subset=columns_merge, keep='first', inplace=True)

        # Saving the order of the columns in the data base
        features = list(df.columns.values)

        # Putting the index in the slicing in order to writting them down easily in the duplicates_check.xlsx
        df = df.reset_index(drop=True)
        df["id_duplicates"] = df.index.values

        # Just in case if it has not been done in the main
        df_manual['match_id'] = df_manual['match_id'].astype('Int32')
        df_manual['id_duplicates'] = df_manual['id_duplicates'].astype('Int32')

        # Correcting the postal code
        if REFORMAT_POSTAL_CODE:
            print("Correcting the postal code...")
            df['code_postal'] = df['code_postal'].astype('Int32')
            df['code_postal'] = df['code_postal'].astype('str')
            for i in range(len(df)):
                code_postal = df.loc[i, "code_postal"]
                code_postal = ("0" * (5 - len(code_postal))) + code_postal
                df.loc[i, "code_postal"] = code_postal

        # Repertoring all the Matches
        # print("Repertoring all the Matches...")
        match = {}
        match_allege = {}
        set_duplicates = set()
        len_process = max(df_manual["match_id"]) + 1
        for match_id in range(len_process):
            df_match_id = df_manual[df_manual["match_id"] == match_id]
            df_match_x = df_match_id[df_match_id["check"] == "x"]
            df_match_id = df_match_id.reset_index(drop=True)
            df_match_x = df_match_x.reset_index(drop=True)
            if len(df_match_x) > 1:
                tab_id_x = df_match_x["id_duplicates"]
                df_x = df[df['id_duplicates'].isin(tab_id_x)]
                df_x = df_x.reset_index(drop=True)
                match[match_id] = df_x
                match_allege[match_id] = df_x['id_duplicates']
                for x in tab_id_x:
                    set_duplicates.add(x)

        # Now we know for each line in db_short if it has a match
        # so we can deduce the lines alones in both the long and short Excel
        alone = [i for i in range(len(df)) if i not in set_duplicates]

        # If a duplicate is present in two match_id, we have to merge the two match_id by keeping the first ones
        # So we check that the intersection of the match id is void
        # print("Repertoring the duplicates of duplicates...")
        match_id_have_to_be_deleted = set()
        for match_id_i, tab_i in match_allege.items():
            for match_id_j, tab_j in match_allege.items():
                if match_id_j > match_id_i:
                    if len(intersection(tab_i, tab_j)) > 0:
                        tab_union = set(list(tab_i + tab_j))
                        match_allege[match_id_i] = tab_union

                        # we have now to copy the operation done on match_allege
                        df_i = match[match_id_i]
                        df_j = match[match_id_j]
                        df_union = pd.concat([df_i, df_j]).drop_duplicates()
                        match[match_id_i] = df_union
                        match_id_have_to_be_deleted.add(match_id_j)

        # print("Deleting the match id duplicate...")
        for match_id_j in match_id_have_to_be_deleted:
            del match[match_id_j]

        print("1/3 analyse done")

        # final DataFrame which will be exported into different excels
        df_merge = pd.DataFrame()

        # We first put in df_merge all the lines coming from the short Excel which have not found a match
        # print("Processing the alones...")

        df_merge = df[df['id_duplicates'].isin(alone)]
        df_merge.loc[:, 'source_duplicates'] = 'alone'
        print("2/3 alones done")

        # Finally puttting in df_merge all the matches
        for match_id, df_match_x in match.items():

            # We compare the element 0 and the element 1
            while len(df_match_x) > 1:
                df_match_x = df_match_x.reset_index(drop=True)
                source_0 = df_match_x.loc[0, "source"]
                source_1 = df_match_x.loc[1, "source"]
                # We copy each column
                for feature in features:
                    feature_0 = df_match_x.loc[0, feature]
                    feature_1 = df_match_x.loc[1, feature]
                    # By default, we will copy feature_0
                    res = feature_0
                    # But , if the element is void
                    if (type(feature_0) == str) and len(feature_0) == 0:
                        res = feature_1
                    # or if the other source is prioritary
                    else:
                        if source_0 not in source_priority.keys() and source_0 in source_priority.keys():
                            res = feature_1
                        if source_0 in source_priority.keys() and source_1 in source_priority.keys():
                            if source_priority[source_0] < source_priority[source_1]:
                                res = feature_1

                    df_match_x.loc[0, feature] = res

                df_match_x = df_match_x.drop([1])
                # Implicit : we keep the source of the greatest priority each time between 0 and 1
            df_match_x["source_duplicates"] = "duplicates"
            df_merge = df_merge.append(df_match_x, sort=False)

        print("3/3 Matches done")

        if self.output_folder != "None":
            print("Now creating the final excel ...")

            # Creating the folder results
            dirName = self.output_folder
            if not os.path.exists(dirName):
                os.mkdir(dirName)
            else:
                print("Directory ", dirName, " already exists, we are overwritting on it ...")

            # Exporting the results
            df_all = df_merge[["source_duplicates"] + features]
            df_all.to_excel("{}/without_duplicates.xlsx".format(self.output_folder), index=False,
                            encoding='utf-8', engine='xlsxwriter')
            print("Done")
