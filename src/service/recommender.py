import os
import pickle
from typing import List, Tuple
from src.utils.logger import logger
from rectools.dataset import Dataset
from rectools.models import load_model


class RecommenderEngine:
    def __init__(self, model_path: str = "/app/models"):
        self.model_path = model_path
        self.ials_model = None
        self.popular_model = None
        self.dataset = None
        self.models_loaded = False

    def load_models(self):
        """Loads models and dataset from pickle files."""
        logger.info("Loading models...")
        try:
            self.ials_model = load_model(os.path.join(self.model_path, "ials.pkl"))
            self.popular_model = load_model(os.path.join(self.model_path, "popular.pkl"))

            # RecTools requires the dataset object for the recommend method
            # to map internal IDs and external IDs and filter viewed items
            with open(os.path.join(self.model_path, "dataset.pkl"), 'rb') as f:
                self.dataset = pickle.load(f)
            
            self.models_loaded = True
            logger.info("Models and dataset loaded successfully.")
        except FileNotFoundError as e:
            logger.error(f"Model files not found: {e}. Waiting for training pipeline.")
            self.models_loaded = False
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self.models_loaded = False

    def recommend(self, user_id: int, k: int = 10) -> Tuple[List[int], str]:
        """
        Returns a list of movie_ids and the type of model used.
        Logic: iALS -> Popular (Cold Start)
        """
        if not self.models_loaded:
            logger.warning("Models are not loaded. Returning empty list.")
            return [], "error"

        # Try Personal Recommender (iALS)
        try:
            # Check if user exists in the dataset mapping
            if user_id in self.dataset.user_id_map.external_ids:
                recs_df = self.ials_model.recommend(
                    users=[user_id],
                    dataset=self.dataset,
                    k=k,
                    filter_viewed=True
                )
                return recs_df["item_id"].tolist(), "personal"
            else:
                logger.info(f"User {user_id} is cold (not in train set).")
        except Exception as e:
            logger.error(f"Error in iALS prediction: {e}")

        # Fallback to Popular
        try:
            recs_df = self.popular_model.recommend(
                users=[user_id],
                dataset=self.dataset,
                k=k,
                filter_viewed=False
            )
            return recs_df["item_id"].tolist(), "popular"
        except Exception as e:
            logger.error(f"Error in Popular prediction: {e}")
            return [], "error"
