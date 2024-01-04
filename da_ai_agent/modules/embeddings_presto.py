import json
from sklearn.metrics.pairwise import cosine_similarity
from transformers import BertTokenizer, BertModel

from da_ai_agent.modules.db_presto import PrestoManager


# TODO: Set up class so it works with PrestoManager, at the moment is only importing PostgresManager. Also,
#  make it aware of the parents component so we choose by default the right manager depending on the databaase we are
#  working on.
class DatabaseEmbedder:
    """
    This class is responsible for embedding database table definitions and
    computing similarity between user queries and table definitions.
    """

    def __init__(self, db: PrestoManager):
        self.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
        self.model = BertModel.from_pretrained("bert-base-uncased")
        self.map_name_to_embeddings = {}
        self.map_name_to_table_def = {}
        self.db = db

    def get_similar_table_defs_for_prompt(self, prompt: str, n_similar=5, n_foreign=0):
        map_table_name_to_table_def = self.db.get_table_definitions_map_for_embeddings()
        for name, table_def in map_table_name_to_table_def.items():
            self.add_table(name, table_def)

        similar_tables = self.get_similar_tables(prompt, n=n_similar)

        table_definitions = self.get_table_definitions_from_names(similar_tables)

        if n_foreign > 0:
            foreign_table_names = self.db.get_foreign_tables(similar_tables, n=3)

            table_definitions = self.get_table_definitions_from_names(
                foreign_table_names + similar_tables
            )

        return table_definitions

    def add_table(self, table_name: str, table_def):
        """
        Convert table definition to a string format suitable for embedding,
        yet store it in the original structured format.
        """
        # Correctly handle table_def as a dictionary
        col_details_str = ' '.join([f"{col_name} {data_type}" for col_name, data_type in table_def.items()])

        self.map_name_to_embeddings[table_name] = self.compute_embeddings(col_details_str)
        self.map_name_to_table_def[table_name] = table_def  # Store the original structure

    def compute_embeddings(self, text):
        """
        Compute embeddings for a given text using the BERT model.
        """
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, padding=True, max_length=512
        )
        outputs = self.model(**inputs)
        return outputs["pooler_output"].detach().numpy()

    def get_similar_tables_via_embeddings(self, query, n=3):
        """
        Given a query, find the top 'n' tables that are most similar to it.

        Args:
        - query (str): The user's natural language query.
        - n (int, optional): Number of top tables to return. Defaults to 3.

        Returns:
        - list: Top 'n' table names ranked by their similarity to the query.
        """
        # Compute the embedding for the user's query
        query_embedding = self.compute_embeddings(query)
        # Calculate cosine similarity between the query and all tables
        similarities = {
            table: cosine_similarity(query_embedding, emb)[0][0]
            for table, emb in self.map_name_to_embeddings.items()
        }
        # Rank tables based on their similarity scores and return top 'n'
        return sorted(similarities, key=similarities.get, reverse=True)[:n]

    def get_similar_table_names_via_word_match(self, query: str):
        """
        if any word in our query is a table name, add the table to a list
        """

        tables = []

        for table_name in self.map_name_to_table_def.keys():
            if table_name.lower() in query.lower():
                tables.append(table_name)

        return tables

    def get_similar_tables(self, query: str, n=3):
        """
        combines results from get_similar_tables_via_embeddings and get_similar_table_names_via_word_match
        """

        similar_tables_via_embeddings = self.get_similar_tables_via_embeddings(query, n)
        similar_tables_via_word_match = self.get_similar_table_names_via_word_match(
            query
        )

        return similar_tables_via_embeddings + similar_tables_via_word_match

    def get_table_definitions_from_names(self, table_names: list):
        """
        Given a list of table names, return their table definitions in the desired format.
        Formats the table definitions as a plain text string suitable for a .txt file.
        """
        formatted_table_defs = ""

        for table_name in table_names:
            table_def = self.map_name_to_table_def[table_name]
            formatted_table_defs += f"{table_name}\n"

            for column_name, data_type in table_def.items():
                formatted_table_defs += f"{column_name}, {data_type}\n"

            formatted_table_defs += "\n"  # Add a blank line between tables for readability

        return formatted_table_defs

    def get_all_table_defs(self):
        """
        Retrieve and print all table definitions.
        """
        map_table_name_to_table_def = self.db.get_table_definitions_map_for_embeddings()
        for name, table_def in map_table_name_to_table_def.items():
            # Pass the table definition directly to add_table
            self.add_table(name, table_def)

        all_table_defs = self.get_table_definitions_from_names(map_table_name_to_table_def.keys())

        # The formatted table definitions are returned
        return all_table_defs
