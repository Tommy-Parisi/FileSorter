from agents.ingestion_manager import IngestionManager
from agents.extractor_router import ExtractorRouter
from agents.embedding_agent import EmbeddingAgent
from agents.clustering_agent import ClusteringAgent
from agents.folder_naming_agent import FolderNamingAgent
from core.models import FileContent
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()

def run_pipeline(input_folder: str, debug_preview: bool = True):
    print(f"\n Starting pipeline on: {input_folder}\n")

    # 1. Ingestion
    ingestor = IngestionManager(input_folder)
    ingestor.scan()

    if not ingestor.file_meta_queue:
        print("  No files found. Check your folder path or filters.")
        return

    print(f" Ingested {len(ingestor.file_meta_queue)} files.\n")

    # 2. Extraction
    router = ExtractorRouter()
    extracted = []

    for fmeta in ingestor.file_meta_queue:
        content: FileContent = router.route(fmeta)
        extracted.append(content)

        status_icon = "GOOD" if content.status == "success" else "FAIL"
        print(f"{status_icon} {fmeta.file_name} → {content.status}")

        if debug_preview and content.status == "success":
            print("----- Extracted Preview -----")
            print(content.raw_text[:500].strip())  # First 500 chars
            print("-----------------------------\n")

    success_count = sum(1 for f in extracted if f.status == "success")
    fail_count = len(extracted) - success_count

    print(f"\n Extraction complete: {success_count} success, {fail_count} failed\n")

    # 3. Embedding
    embedder = EmbeddingAgent()
    embedded = []

    for extracted_file in extracted:
        embedded_file = embedder.embed(extracted_file)
        embedded.append(embedded_file)

    print(f"\nEmbedded {len([e for e in embedded if e.status == 'embedded'])} documents successfully.")

    # Print a few example embeddings
    print("\n--- Sample Embeddings ---")

    for embedded_file in embedded[:25]:  # Show first 5 for sanity
        if embedded_file.status == "embedded":
            print(f"{embedded_file.file_meta.file_name}")
            print(f"Embedding (first 5 values): {embedded_file.embedding[:5]}")
            print(f"Vector length: {len(embedded_file.embedding)}\n")

    # 4. Clustering
    clusterer = ClusteringAgent(n_clusters = max(2, len(embedded) // 5) ) 
    clustered = clusterer.cluster(embedded)

    if clustered:
        n_clusters = len(set(f.cluster_id for f in clustered))
        print(f"\nClustering complete: {n_clusters} clusters\n")

        cluster_map = defaultdict(list)
    for f in clustered:
        cluster_map[f.cluster_id].append(f)

    # Log each cluster and its members
    print("\n--- Cluster Breakdown ---")
    for cluster_id, files in sorted(cluster_map.items()):
        print(f"\nCluster {cluster_id} ({len(files)} file{'s' if len(files) != 1 else ''}):")
        for f in files:
            print(f"  - {f.file_meta.file_name}")

    # 5. Folder Naming
    naming_agent = FolderNamingAgent()
    folder_names = naming_agent.name_clusters(cluster_map)

    print("\n--- Final Cluster Labels ---")
    for cluster_id, files in sorted(cluster_map.items()):
        label = folder_names.get(cluster_id, f"cluster_{cluster_id}")
        print(f"\n{label} (Cluster {cluster_id}) — {len(files)} file{'s' if len(files) != 1 else ''}")
        for f in files:
            print(f"  - {f.file_meta.file_name}")


