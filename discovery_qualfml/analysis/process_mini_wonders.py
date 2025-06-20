import os
import pandas as pd

from discovery_qualfml import PROJECT_DIR

folder_path = PROJECT_DIR / "data/mini_wonders2"  # Change to your actual local path

all_rows = []

for file_name in os.listdir(folder_path):
    if not file_name.endswith(".xlsx"):
        continue

    file_path = os.path.join(folder_path, file_name)

    # Read file with no header to locate the true header row
    df = pd.read_excel(file_path, header=10)

    component_col = "Component"
    rating_col = "Rating Explanation (examples, quotes) + additional comments"

    # Process each row
    base_id = os.path.splitext(file_name)[0].replace(" ", "_")
    for _, row in df.iterrows():
        component = row.get(component_col)
        rating = row.get(rating_col)

        if pd.notna(component) and pd.notna(rating):
            # Question
            all_rows.append(
                {
                    "conversation_id": base_id,
                    "text_id": f"{base_id}_{len(all_rows) + 1}",
                    "role": "question",
                    "text": str(component).strip(),
                }
            )
            # Response
            all_rows.append(
                {
                    "conversation_id": base_id,
                    "text_id": f"{base_id}_{len(all_rows) + 1}",
                    "role": "response",
                    "text": str(rating).strip(),
                }
            )

# 3. Create and preview final DataFrame
transcript_df = pd.DataFrame(all_rows)


transcript_df.to_csv(PROJECT_DIR / "data/mini_wonders/fidelity_checklist_transcript.csv", index=False)
