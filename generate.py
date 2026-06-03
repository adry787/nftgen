"""NFT Gen - Metadata generator for NFT collections."""

import os
import json
import math
import random
import hashlib
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TraitDefinition:
    trait_type: str
    values: list[dict]  # [{"value": "Red", "weight": 0.3}, ...]

    def weighted_choice(self, rng: random.Random) -> str:
        total_weight = sum(v.get("weight", 1.0) for v in self.values)
        r = rng.random() * total_weight
        cumulative = 0.0
        for v in self.values:
            cumulative += v.get("weight", 1.0)
            if r <= cumulative:
                return v["value"]
        return self.values[-1]["value"]


@dataclass
class NFTMetadata:
    name: str
    description: str
    image: str = ""
    attributes: list[dict] = field(default_factory=list)
    external_url: str = ""
    animation_url: str = ""

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "description": self.description,
            "attributes": self.attributes,
        }
        if self.image:
            d["image"] = self.image
        if self.external_url:
            d["external_url"] = self.external_url
        if self.animation_url:
            d["animation_url"] = self.animation_url
        return d


class RarityCalculator:
    """Calculate rarity scores for NFT traits."""

    @staticmethod
    def calculate_trait_rarity(trait_counts: dict[str, dict[str, int]],
                                total: int) -> dict[str, dict[str, float]]:
        rarity_scores = {}
        for trait_type, value_counts in trait_counts.items():
            rarity_scores[trait_type] = {}
            for value, count in value_counts.items():
                rarity_scores[trait_type][value] = total / max(count, 1)
        return rarity_scores

    @staticmethod
    def calculate_item_rarity(attributes: list[dict],
                               trait_rarity: dict[str, dict[str, float]]) -> float:
        score = 0.0
        for attr in attributes:
            trait_type = attr.get("trait_type", "")
            value = attr.get("value", "")
            if trait_type in trait_rarity and value in trait_rarity[trait_type]:
                score += trait_rarity[trait_type][value]
        return round(score, 4)


class NFTCollectionGenerator:
    """Generate complete NFT metadata collections."""

    def __init__(self, name: str = "My Collection", description: str = ""):
        self.name = name
        self.description = description or f"{name} - Generative NFT Collection"
        self.traits: list[TraitDefinition] = []
        self.metadata_list: list[NFTMetadata] = []
        self.rarity_calc = RarityCalculator()

    def add_trait(self, trait_type: str, values: list[dict]) -> None:
        self.traits.append(TraitDefinition(trait_type=trait_type, values=values))

    def load_config(self, path: str) -> None:
        with open(path) as f:
            config = json.load(f)
        self.name = config.get("name", self.name)
        self.description = config.get("description", self.description)
        for t in config.get("traits", []):
            self.add_trait(t["type"], t["values"])

    def generate_single(self, token_id: int, rng: random.Random,
                         base_uri: str = "") -> NFTMetadata:
        attributes = []
        for trait in self.traits:
            value = trait.weighted_choice(rng)
            attributes.append({"trait_type": trait.trait_type, "value": value})

        image_name = f"{token_id}.png"
        image_path = f"{base_uri}/{image_name}" if base_uri else image_name

        metadata = NFTMetadata(
            name=f"#{token_id}",
            description=f"{self.name} #{token_id}",
            image=image_path,
            attributes=attributes,
        )
        return metadata

    def generate_collection(self, count: int, seed: int = 42,
                             base_uri: str = "", exclude_duplicates: bool = True,
                             max_attempts: int = 10) -> list[NFTMetadata]:
        rng = random.Random(seed)
        self.metadata_list = []
        seen_combos: set[str] = set()

        for i in range(1, count + 1):
            for attempt in range(max_attempts):
                meta = self.generate_single(i, rng, base_uri)
                combo_key = self._combo_key(meta.attributes)

                if not exclude_duplicates or combo_key not in seen_combos:
                    seen_combos.add(combo_key)
                    self.metadata_list.append(meta)
                    break
            else:
                self.metadata_list.append(meta)

        self._calculate_rarities()
        logger.info("Generated %d NFTs with %d unique combinations",
                     len(self.metadata_list), len(seen_combos))
        return self.metadata_list

    def _combo_key(self, attributes: list[dict]) -> str:
        parts = sorted(f"{a['trait_type']}:{a['value']}" for a in attributes)
        return "|".join(parts)

    def _calculate_rarities(self) -> None:
        trait_counts: dict[str, dict[str, int]] = {}
        for meta in self.metadata_list:
            for attr in meta.attributes:
                tt = attr["trait_type"]
                val = attr["value"]
                if tt not in trait_counts:
                    trait_counts[tt] = {}
                trait_counts[tt][val] = trait_counts[tt].get(val, 0) + 1

        self.trait_rarity = self.rarity_calc.calculate_trait_rarity(
            trait_counts, len(self.metadata_list)
        )

        for meta in self.metadata_list:
            rarity_score = self.rarity_calc.calculate_item_rarity(
                meta.attributes, self.trait_rarity
            )
            meta.attributes.append({
                "trait_type": "Rarity Score",
                "value": str(rarity_score),
            })

    def get_statistics(self) -> dict:
        if not self.metadata_list:
            return {"error": "No collection generated"}

        total = len(self.metadata_list)
        trait_stats = {}
        for meta in self.metadata_list:
            for attr in meta.attributes:
                if attr["trait_type"] == "Rarity Score":
                    continue
                tt = attr["trait_type"]
                val = attr["value"]
                if tt not in trait_stats:
                    trait_stats[tt] = {}
                trait_stats[tt][val] = trait_stats[tt].get(val, 0) + 1

        trait_summary = {}
        for tt, vals in trait_stats.items():
            trait_summary[tt] = {
                "unique_values": len(vals),
                "distribution": {v: round(c / total, 4) for v, c in vals.items()},
            }

        rarity_scores = []
        for meta in self.metadata_list:
            for attr in meta.attributes:
                if attr["trait_type"] == "Rarity Score":
                    try:
                        rarity_scores.append(float(attr["value"]))
                    except ValueError:
                        pass

        return {
            "collection": self.name,
            "total_nfts": total,
            "unique_combinations": len(set(
                self._combo_key(m.attributes[:-1]) for m in self.metadata_list
            )),
            "trait_stats": trait_summary,
            "rarity_stats": {
                "mean": round(sum(rarity_scores) / max(len(rarity_scores), 1), 4),
                "min": round(min(rarity_scores), 4) if rarity_scores else 0,
                "max": round(max(rarity_scores), 4) if rarity_scores else 0,
            },
        }

    def export(self, output_dir: str, base_uri: str = "") -> str:
        os.makedirs(output_dir, exist_ok=True)
        metadata_dir = os.path.join(output_dir, "metadata")
        os.makedirs(metadata_dir, exist_ok=True)

        for meta in self.metadata_list:
            token_id = meta.name.replace("#", "")
            path = os.path.join(metadata_dir, f"{token_id}.json")
            with open(path, "w") as f:
                json.dump(meta.to_dict(), f, indent=2)

        stats = self.get_statistics()
        stats_path = os.path.join(output_dir, "collection_stats.json")
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)

        collection_meta = {
            "name": self.name,
            "description": self.description,
            "symbol": self.name[:4].upper().replace(" ", ""),
            "total_supply": len(self.metadata_list),
            "base_uri": base_uri,
        }
        with open(os.path.join(output_dir, "collection.json"), "w") as f:
            json.dump(collection_meta, f, indent=2)

        logger.info("Exported %d metadata files to %s", len(self.metadata_list), output_dir)
        return output_dir


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="NFT Metadata Generator")
    parser.add_argument("--collection", type=str, default="My Collection")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--config", type=str, help="Collection config JSON")
    parser.add_argument("--output", type=str, default="output")
    parser.add_argument("--base-uri", type=str, default="ipfs://")
    args = parser.parse_args()

    gen = NFTCollectionGenerator(args.collection)

    if args.config:
        gen.load_config(args.config)
    else:
        gen.add_trait("Background", [
            {"value": "Blue", "weight": 0.3},
            {"value": "Red", "weight": 0.2},
            {"value": "Green", "weight": 0.2},
            {"value": "Purple", "weight": 0.15},
            {"value": "Gold", "weight": 0.1},
            {"value": "Diamond", "weight": 0.05},
        ])
        gen.add_trait("Body", [
            {"value": "Human", "weight": 0.4},
            {"value": "Robot", "weight": 0.3},
            {"value": "Alien", "weight": 0.2},
            {"value": "Zombie", "weight": 0.1},
        ])
        gen.add_trait("Eyes", [
            {"value": "Normal", "weight": 0.35},
            {"value": "Laser", "weight": 0.15},
            {"value": "Cyclops", "weight": 0.1},
            {"value": "3D", "weight": 0.2},
            {"value": "Heart", "weight": 0.2},
        ])

    metadatas = gen.generate_collection(args.count, seed=args.seed, base_uri=args.base_uri)
    gen.export(args.output, base_uri=args.base_uri)

    stats = gen.get_statistics()
    print(json.dumps(stats, indent=2))
    print(f"\nGenerated {len(metadatas)} NFTs in {args.output}/")
