import pandas as pd
from mlxtend.frequent_patterns import fpgrowth, association_rules
from mlxtend.preprocessing import TransactionEncoder

# Voahangy n'aura plus qu'à remplacer 'dataset_propre' par son dataframe
def get_association_rules(transactions_df, min_support=0.05, min_lift=1.2):
    te = TransactionEncoder()
    te_ary = te.fit_transform(transactions_df)
    df = pd.DataFrame(te_ary, columns=te.columns_)
    
    # FP-Growth (plus rapide qu'Apriori)
    frequent_itemsets = fpgrowth(df, min_support=min_support, use_colnames=True)
    
    # Filtrage par le Lift
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
    
    # On garde le top (ex: confiance > 0.6)
    top_rules = rules[rules["confidence"] >= 0.6].sort_values("lift", ascending=False)
    
    return top_rules.head(5)