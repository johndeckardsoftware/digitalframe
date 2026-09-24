import logging
import os
import threading
import time
import numpy as np
from PIL import Image
from datetime import datetime
import torch
from transformers import CLIPModel, CLIPProcessor

from config import ItemType
from config import Config

logger = logging.getLogger(__name__)

class ImageFeatureIndexer:

    def __init__(
        self,
        df_item_list,
        start_time=None,
        end_time=None,
        model_name="openai/clip-vit-base-patch32",
    ):
        """BACKGROUND CLIP FEATURE INDEXER FOR DIGITALFRAME.

        :param df_item_list: Instance of DFItemList containing loaded items
        :param start_time: "HH:MM" (24h) string indicating when background
        processing starts
        :param end_time: "HH:MM" (24h) string indicating when background
        processing ends
        :param model_name: Hugging Face model identifier for CLIP
        """
        self.df_item_list = df_item_list
        self.start_time = datetime.strptime(start_time if start_time else Config.get('indexer.start', "00:00"), "%H:%M").time()
        self.end_time = datetime.strptime(end_time if end_time else Config.get('indexer.end', "23:59"), "%H:%M").time()
        self.model_name = model_name

        self.model = None
        self.processor = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # Used with df_item_list.last_load to wakeup _indexing_worker thread
        self.last_load = None

        # selection
        self.labels = Config.get('indexer.labels', "")
        self.max_results = Config.get('indexer.max_results', 0)
        self.threshold = Config.get('indexer.threshold', 22)
        self.selected = None

        # Cache of loaded embeddings: { image_file_path: numpy_array(shape=(512,)) }
        self.embeddings_cache = {}

        # Pre-load existing saved features from disk
        #self._load_cached_embeddings()

        # Start background indexing worker thread
        self.worker_thread = threading.Thread(target=self._indexing_worker, daemon=True)
        self.worker_thread.start()

    def _init_model(self):
        """Lazy initialization of CLIP model to save RAM until needed."""
        if self.model is None:
            logger.info("Initializing CLIP model for feature extraction...")
            self.model = CLIPModel.from_pretrained(self.model_name)
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model.eval()

    def _is_in_time_window(self) -> bool:
        """Check if current system time falls within the configured work window."""
        now = datetime.now().time()
        if self.start_time <= self.end_time:
            return self.start_time <= now <= self.end_time
        else:  # Handles overnight ranges (e.g. 23:00 to 04:00)
            return now >= self.start_time or now <= self.end_time

    def _get_feature_path(self, image_path: str) -> str:
        """Returns the cache path for saving .npy feature files."""
        return f"{image_path}.clip.npy"

    def _load_cached_embeddings(self):
        """Loads all existing .npy embeddings already stored on disk."""
        count = 0
        with self._lock:
            for item in self.df_item_list.items:
                if item.type == ItemType.IMAGE:
                    feat_path = self._get_feature_path(item.file)
                    if os.path.exists(feat_path):
                        try:
                            feat = np.load(feat_path)
                            self.embeddings_cache[item.file] = feat
                            count += 1
                            time.sleep(0.01)
                        except Exception as e:
                            logger.error(f"Failed loading cached feature for {item.file}: {e}")
        logger.info(f"{count} image features loaded from cache.")

    def _extract_and_save_feature(self, image_path: str) -> np.ndarray:
        """Extracts L2-normalized embedding for a single image and saves it to disk."""
        self._init_model()
        with Image.open(image_path) as img:
            image_rgb = img.convert("RGB")
            # Thumbnail resizes in-place maintaining aspect ratio (e.g. 800x800 max)
            # This reduces 4K image processing overhead significantly
            image_rgb.thumbnail((800, 800), Image.Resampling.LANCZOS)
            inputs = self.processor(images=image_rgb, return_tensors="pt")

            with torch.no_grad():
                outputs = self.model.get_image_features(**inputs)
                # Check if outputs is a dataclass wrapper or directly a Tensor
                if hasattr(outputs, "image_embeds"):
                    feat = outputs.image_embeds
                elif hasattr(outputs, "pooler_output"):
                    feat = outputs.pooler_output
                else:
                    feat = outputs
                # L2 normalization
                feat = feat / feat.norm(dim=-1, keepdim=True)
                feat_np = feat.squeeze(0).cpu().numpy()

        # Save binary embedding file to disk
        feat_path = self._get_feature_path(image_path)
        np.save(feat_path, feat_np)
        return feat_np

    def _indexing_worker(self):
        """Background worker thread processing un-indexed images during scheduled window."""
        logger.info("ImageFeatureIndexer thread started.")
        time.sleep(60)
        self._load_cached_embeddings()

        while not self._stop_event.is_set():
            if (not self.last_load or self.last_load != self.df_item_list.last_load) and self._is_in_time_window():
                # Take a snapshot copy of current image items
                image_items = [item for item in self.df_item_list.items if item.type == ItemType.IMAGE]

                for item in image_items:
                    if self._stop_event.is_set():
                        break

                    # Exit early if time window closes mid-processing
                    if not self._is_in_time_window():
                        logger.info("Feature indexing time window closed. Pausing background indexing.")
                        break

                    # Skip if already cached
                    if item.file in self.embeddings_cache:
                        logger.debug(f"{item.file} already cached.")
                        continue

                    try:
                        feat_np = self._extract_and_save_feature(item.file)
                        with self._lock:
                            self.embeddings_cache[item.file] = feat_np
                        logger.info(f"Generated and saved feature vector for: {item.name}")
                    except Exception as e:
                        logger.error(f"Error extracting features for {item.file}: {e}")

                    # Brief sleep to avoid thermal throttling/starving main Raylib GUI thread
                    time.sleep(2.0)

                self.last_load = self.df_item_list.last_load

            # Check schedule every 60 seconds when idle
            time.sleep(60)

    def set_labels(self, labels):
        if labels and len(labels) > 0:
            self.labels = labels
            Config.set('indexer.labels', labels)
            ret = labels.split(",") 
        else:
            self.labels = ""
            self.selected = None
            ret = None
        # save labels
        recent = Config.get('indexer.recent_labels', [])
        if not labels in recent:
            recent.append(labels)
            Config.set('indexer.recent_labels', recent)
        return ret
    
    def get_labels(self):
        return self.labels

    def reset_selected(self):
        self.selected = None

    def set_threshold(self, value, delta=True):
        self.threshold = self.threshold + value if delta else value
        self.threshold = max(1, min(self.threshold, 100))
        Config.set('indexer.threshold', self.threshold)

    def get_threshold(self):
        return self.threshold

    def set_max_results(self, value, delta=True):
        self.max_results = self.max_results + value if delta else value
        self.max_results = max(0, min(self.max_results, 255))
        Config.set('indexer.max_results', self.max_results)

    def get_max_results(self):
        return self.max_results

    def find_photos(self, query_labels) -> list[dict]:
        """Exposes vectorized matching against processed photos.

        :param query_labels: text queries (e.g. "cycling, beach, sunset")
        :return: Ranked list of matches with photo references and similarity  scores
        """
        list_labels = self.set_labels(query_labels)
        if not list_labels: return None

        self._init_model()

        threshold = self.threshold / 100

        with self._lock:
            cached_files = list(self.embeddings_cache.keys())
            if not cached_files:
                return []

            # Stack saved 1D numpy arrays into 2D Matrix of shape (N_photos, D_features)
            image_vectors = np.array([self.embeddings_cache[f] for f in cached_files])

        image_tensor = torch.tensor(image_vectors, dtype=torch.float32)

        # Encode text queries
        text_inputs = self.processor(
            text=[f"a photo of {label}" for label in list_labels],
            return_tensors="pt",
            padding=True,
        )

        with torch.no_grad():
            outputs = self.model.get_text_features(**text_inputs)
            # Check if outputs is a dataclass wrapper or directly a Tensor
            if hasattr(outputs, "text_embeds"):
                text_features = outputs.text_embeds
            elif hasattr(outputs, "pooler_output"):
                text_features = outputs.pooler_output
            else:
                text_features = outputs

            # L2 Normalization
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

            # Cosine Similarity matrix: shape (N_photos, M_queries)
            # Resulting values range from -1.0 to 1.0 (typically 0.15 to 0.35 for CLIP)
            similarity = image_tensor @ text_features.T

            # Max score across candidate queries per image
            max_scores, best_label_indices = similarity.max(dim=-1)

        results = []
        for idx, (score, label_idx) in enumerate(zip(max_scores, best_label_indices)):
            score_val = score.item()
            if score_val >= threshold:
                results.append(
                    {
                        "file": cached_files[idx],
                        "matched_label": list_labels[label_idx.item()],
                        "score": round(score_val, 4), # or round(score_val * 100, 2)
                    }
                )

        # Sort descending by match confidence
        results.sort(key=lambda x: x["score"], reverse=True)
        max_results = len(results) if self.max_results == 0 else self.max_results
        self.selected = results[:max_results]

    def stop(self):
        self._stop_event.set()
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        logger.info("ImageFeatureIndexer thread stopped.")
