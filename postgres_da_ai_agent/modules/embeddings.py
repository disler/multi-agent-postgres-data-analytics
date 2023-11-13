from sklearn.metrics.pairwise import cosine_similarity
from transformers import BertTokenizer, BertModel

from postgres_da_ai_agent.modules.db import PostgresManager


class DatabaseEmbedder:
    """
    This class is responsible for embedding database table definitions and
    computing similarity between user queries and table definitions.
    """

    def __init__(self, db: PostgresManager):
        self.tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
        self.model = BertModel.from_pretrained("bert-base-uncased")
        self.map_name_to_embeddings = {}
        self.map_name_to_table_def = {}
        self.db = db

    def get_similar_table_defs_for_prompt(self, prompt: str, n_similar=5, n_foreign=0):
        map_table_name_to_table_def = self.db.get_table_definition_map_for_embeddings()
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

    def add_table(self, table_name: str, text_representation: str):
        """
        Add a table to the database embedder.
        Map the table name to its embedding and text representation.
        """
        self.map_name_to_embeddings[table_name] = self.compute_embeddings(
            text_representation
        )

        self.map_name_to_table_def[table_name] = text_representation

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

    def get_table_definitions_from_names(self, table_names: list) -> str:
        """
        Given a list of table names, return their table definitions.
        """
        table_defs = [
            self.map_name_to_table_def[table_name] for table_name in table_names
        ]
        return "\n\n".join(table_defs)
