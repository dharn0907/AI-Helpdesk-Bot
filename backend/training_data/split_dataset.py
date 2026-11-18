
import pandas as pd
from sklearn.model_selection import train_test_split
from pathlib import Path

# Dataset paths
BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "human_intervention_dataset_2100.csv"

# Load dataset
df = pd.read_csv(DATASET_PATH)

# First split: 80% training, 20% temporary
train_df, temp_df = train_test_split(
    df,
    test_size=0.20,
    stratify=df["label"],
    random_state=42
)

# Second split: divide temporary data equally
validation_df, test_df = train_test_split(
    temp_df,
    test_size=0.50,
    stratify=temp_df["label"],
    random_state=42
)

# Save datasets
train_df.to_csv(BASE_DIR / "train.csv", index=False)
validation_df.to_csv(BASE_DIR / "validation.csv", index=False)
test_df.to_csv(BASE_DIR / "test.csv", index=False)

# Display results
print("Dataset splitting completed!")
print("Training samples:", len(train_df))
print("Validation samples:", len(validation_df))
print("Testing samples:", len(test_df))

print("\nTraining distribution:")
print(train_df["label"].value_counts())

print("\nValidation distribution:")
print(validation_df["label"].value_counts())

print("\nTesting distribution:")
print(test_df["label"].value_counts())
