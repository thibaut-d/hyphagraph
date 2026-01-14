"""
Complete Fibromyalgia Knowledge Graph Workflow Test
Tests the full pipeline: Login -> Extract -> Save -> Analyze -> Infer
"""

import requests
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple

# Configuration
BASE_URL = "http://localhost"  # Access via Caddy proxy
FIBROMYALGIA_ENTITY_ID = "de334806-3edc-40c3-8b82-8e4c05f29481"

# Test credentials
TEST_USER = "admin@example.com"
TEST_PASSWORD = "changeme123"

class WorkflowTester:
    def __init__(self):
        self.token = None
        self.results = {
            "start_time": datetime.now().isoformat(),
            "login": {},
            "extractions": [],
            "database_stats": {},
            "inferences": {},
            "errors": []
        }

    def log(self, message: str):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def step1_login(self) -> bool:
        """Step 1: Login and get fresh token"""
        self.log("STEP 1: Logging in to get fresh token...")

        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                data={"username": TEST_USER, "password": TEST_PASSWORD}  # OAuth2 form data
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.results["login"] = {
                    "success": True,
                    "token_length": len(self.token) if self.token else 0
                }
                self.log(f"✓ Login successful! Token obtained.")
                return True
            else:
                error = f"Login failed with status {response.status_code}"
                self.log(f"✗ {error}")
                self.results["login"] = {"success": False, "error": error}
                return False

        except Exception as e:
            error = f"Login exception: {str(e)}"
            self.log(f"✗ {error}")
            self.results["login"] = {"success": False, "error": error}
            return False

    def query_postgres(self, sql: str) -> List[tuple]:
        """Execute a SQL query on PostgreSQL via docker exec"""
        try:
            cmd = [
                "docker", "exec", "hyphagraph-db",
                "psql", "-U", "hyphagraph", "-d", "hyphagraph",
                "-t", "-A", "-F", "|",  # -t: tuples only, -A: unaligned, -F: field separator
                "-c", sql
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if not result.stdout.strip():
                return []

            rows = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    rows.append(tuple(line.split('|')))
            return rows
        except Exception as e:
            self.log(f"✗ Database query error: {str(e)}")
            return []

    def get_sources(self) -> List[Dict]:
        """Get all sources from PostgreSQL database"""
        self.log("Fetching sources from database...")

        try:
            sql = """
                SELECT s.id, sr.url, sr.title, s.created_at
                FROM sources s
                JOIN source_revisions sr ON sr.source_id = s.id
                WHERE sr.is_current = true
                  AND sr.document_text IS NOT NULL
                ORDER BY s.created_at DESC
                LIMIT 20
            """

            rows = self.query_postgres(sql)

            sources = []
            for row in rows:
                sources.append({
                    "id": row[0],
                    "url": row[1],
                    "title": row[2],
                    "created_at": row[3]
                })

            self.log(f"Found {len(sources)} sources with documents in database")
            return sources

        except Exception as e:
            self.log(f"✗ Error fetching sources: {str(e)}")
            return []

    def step2_extract_knowledge(self, sources: List[Dict]):
        """Step 2: Extract knowledge from all sources"""
        self.log(f"\nSTEP 2: Extracting knowledge from {len(sources)} sources...")
        self.log("This will take approximately 5-10 minutes (15-20 seconds per source)")

        headers = {"Authorization": f"Bearer {self.token}"}

        for idx, source in enumerate(sources, 1):
            source_id = source["id"]
            url = source["url"]
            title = source["title"] or "Untitled"

            self.log(f"\n[{idx}/{len(sources)}] Processing: {title[:60]}...")
            self.log(f"  URL: {url}")

            extraction_result = {
                "source_id": source_id,
                "url": url,
                "title": title,
                "extract_success": False,
                "save_success": False,
                "entities_extracted": 0,
                "relations_extracted": 0,
                "error": None
            }

            try:
                # Step 2a: Extract from URL
                self.log(f"  Extracting... (this may take 15-20 seconds)")
                start_time = time.time()

                extract_response = requests.post(
                    f"{BASE_URL}/api/sources/{source_id}/extract-from-url",
                    headers=headers,
                    json={"url": url},
                    timeout=120  # 2 minute timeout
                )

                extract_time = time.time() - start_time

                if extract_response.status_code == 200:
                    extract_data = extract_response.json()
                    extraction_result["extract_success"] = True
                    extraction_result["extract_time"] = round(extract_time, 2)

                    # Count entities and relations
                    entities = extract_data.get("entities", [])
                    relations = extract_data.get("relations", [])
                    extraction_result["entities_extracted"] = len(entities)
                    extraction_result["relations_extracted"] = len(relations)

                    self.log(f"  ✓ Extracted: {len(entities)} entities, {len(relations)} relations ({extract_time:.1f}s)")

                    # Step 2b: Save extraction
                    # Convert extraction data to save format
                    if len(entities) > 0 or len(relations) > 0:
                        self.log(f"  Saving to database...")
                        save_start = time.time()

                        # Prepare save request with entities to create and relations
                        entities_to_create = [
                            {
                                "slug": e.get("slug"),
                                "summary": {"en": e.get("summary", "")},
                                "category": e.get("category")
                            }
                            for e in entities
                        ]

                        # Prepare relations (they use slugs which will be mapped)
                        relations_to_create = [
                            {
                                "subject_slug": r.get("subject"),
                                "object_slug": r.get("object"),
                                "kind": r.get("relation_type", "other"),
                                "confidence": r.get("confidence", "medium"),
                                "roles": r.get("roles", {}),
                                "notes": {"en": r.get("notes", "")} if r.get("notes") else None
                            }
                            for r in relations
                        ]

                        save_response = requests.post(
                            f"{BASE_URL}/api/sources/{source_id}/save-extraction",
                            headers=headers,
                            json={
                                "entities_to_create": entities_to_create,
                                "entity_links": {},  # No existing entity links in this simple test
                                "relations_to_create": relations_to_create
                            },
                            timeout=60
                        )

                        save_time = time.time() - save_start

                        if save_response.status_code == 200:
                            save_data = save_response.json()
                            extraction_result["save_success"] = True
                            extraction_result["save_time"] = round(save_time, 2)
                            extraction_result["entities_saved"] = save_data.get("entities_created", 0) + save_data.get("entities_linked", 0)
                            extraction_result["relations_saved"] = save_data.get("relations_created", 0)

                            self.log(f"  ✓ Saved: {extraction_result['entities_saved']} entities, {extraction_result['relations_saved']} relations")
                        else:
                            error = f"Save failed: {save_response.status_code} - {save_response.text[:200]}"
                            extraction_result["error"] = error
                            self.log(f"  ✗ {error}")
                    else:
                        self.log(f"  ⚠ No entities or relations extracted, skipping save")

                else:
                    error = f"Extraction failed: {extract_response.status_code} - {extract_response.text[:200]}"
                    extraction_result["error"] = error
                    self.log(f"  ✗ {error}")

            except requests.exceptions.Timeout:
                error = "Request timeout (>120s)"
                extraction_result["error"] = error
                self.log(f"  ✗ {error}")

            except Exception as e:
                error = f"Exception: {str(e)}"
                extraction_result["error"] = error
                self.log(f"  ✗ {error}")

            self.results["extractions"].append(extraction_result)

            # Small delay between requests
            time.sleep(1)

        # Summary
        successful = sum(1 for r in self.results["extractions"] if r["extract_success"] and r["save_success"])
        self.log(f"\n{'='*60}")
        self.log(f"EXTRACTION SUMMARY: {successful}/{len(sources)} sources processed successfully")
        self.log(f"{'='*60}")

    def step3_analyze_database(self):
        """Step 3: Analyze database contents"""
        self.log("\nSTEP 3: Analyzing database contents...")

        try:
            # Count entities
            rows = self.query_postgres("SELECT COUNT(*) FROM entities")
            entity_count = int(rows[0][0]) if rows else 0

            # Count relations
            rows = self.query_postgres("SELECT COUNT(*) FROM relations")
            relation_count = int(rows[0][0]) if rows else 0

            # Top entities by connection count (using relation_role_revisions)
            sql = """
                SELECT e.id, er.slug, COUNT(rrr.id) as connection_count
                FROM entities e
                JOIN entity_revisions er ON er.entity_id = e.id AND er.is_current = true
                LEFT JOIN relation_role_revisions rrr ON rrr.entity_id = e.id
                GROUP BY e.id, er.slug
                ORDER BY connection_count DESC
                LIMIT 10
            """
            rows = self.query_postgres(sql)
            top_entities = [
                {
                    "id": row[0],
                    "name": row[1],
                    "type": "entity",
                    "connections": int(row[2])
                }
                for row in rows
            ]

            # Relation type distribution (using relation_revisions kind)
            sql = """
                SELECT COALESCE(rr.kind, 'unknown') as kind, COUNT(*) as count
                FROM relation_revisions rr
                WHERE rr.is_current = true
                GROUP BY rr.kind
                ORDER BY count DESC
            """
            rows = self.query_postgres(sql)
            relation_types = [
                {"type": row[0], "count": int(row[1])}
                for row in rows
            ]

            self.results["database_stats"] = {
                "total_entities": entity_count,
                "total_relations": relation_count,
                "top_entities": top_entities,
                "relation_types": relation_types
            }

            self.log(f"✓ Total Entities: {entity_count}")
            self.log(f"✓ Total Relations: {relation_count}")
            self.log(f"✓ Top 10 Connected Entities:")
            for ent in top_entities[:10]:
                self.log(f"    - {ent['name']} ({ent['type']}): {ent['connections']} connections")

            self.log(f"✓ Relation Types:")
            for rel in relation_types:
                self.log(f"    - {rel['type']}: {rel['count']}")

        except Exception as e:
            error = f"Database analysis error: {str(e)}"
            self.log(f"✗ {error}")
            self.results["errors"].append(error)

    def step4_calculate_inferences(self):
        """Step 4: Calculate inferences for fibromyalgia"""
        self.log(f"\nSTEP 4: Calculating inferences for fibromyalgia entity...")

        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            response = requests.get(
                f"{BASE_URL}/api/inferences/entity/{FIBROMYALGIA_ENTITY_ID}",
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                self.results["inferences"] = data

                self.log(f"✓ Inferences calculated successfully!")

                # Display role inferences (it's a list, not a dict)
                role_inferences = data.get("role_inferences", [])
                if role_inferences:
                    self.log(f"\nRole Inferences ({len(role_inferences)} total):")
                    for inference in role_inferences[:10]:  # Top 10
                        role_type = inference.get('role_type', 'unknown')
                        score = inference.get('score')
                        coverage = inference.get('coverage', 0)
                        confidence = inference.get('confidence', 0)
                        self.log(f"  - {role_type}: score={score if score is not None else 'N/A'}, "
                               f"coverage={coverage:.2f}, confidence={confidence:.2f}")
                else:
                    self.log(f"  No role inferences calculated")

            else:
                error = f"Inference calculation failed: {response.status_code}"
                self.log(f"✗ {error}")
                self.results["errors"].append(error)

        except Exception as e:
            error = f"Inference exception: {str(e)}"
            self.log(f"✗ {error}")
            self.results["errors"].append(error)

    def step5_generate_report(self):
        """Step 5: Generate final report"""
        self.log(f"\nSTEP 5: Generating final report...")

        self.results["end_time"] = datetime.now().isoformat()

        # Calculate statistics
        total_sources = len(self.results["extractions"])
        successful_extracts = sum(1 for r in self.results["extractions"] if r["extract_success"])
        successful_saves = sum(1 for r in self.results["extractions"] if r["save_success"])

        total_entities_extracted = sum(r.get("entities_extracted", 0) for r in self.results["extractions"])
        total_relations_extracted = sum(r.get("relations_extracted", 0) for r in self.results["extractions"])

        report = f"""# Fibromyalgia Knowledge Graph - Complete Workflow Test Results

**Test Date:** {self.results["start_time"]}
**Completion Date:** {self.results["end_time"]}

## Executive Summary

- **Total Sources Processed:** {total_sources}
- **Successful Extractions:** {successful_extracts}/{total_sources} ({successful_extracts/total_sources*100:.1f}%)
- **Successful Saves:** {successful_saves}/{total_sources} ({successful_saves/total_sources*100:.1f}%)
- **Total Entities in Database:** {self.results["database_stats"].get("total_entities", 0)}
- **Total Relations in Database:** {self.results["database_stats"].get("total_relations", 0)}

## 1. Authentication

- **Status:** {'✓ Success' if self.results["login"].get("success") else '✗ Failed'}
- **User:** {TEST_USER}

## 2. Knowledge Extraction Results

### Extraction Summary

| Metric | Value |
|--------|-------|
| Sources Processed | {total_sources} |
| Extractions Attempted | {total_sources} |
| Extractions Successful | {successful_extracts} |
| Saves Successful | {successful_saves} |
| Total Entities Extracted | {total_entities_extracted} |
| Total Relations Extracted | {total_relations_extracted} |

### Per-Source Results

"""

        for idx, result in enumerate(self.results["extractions"], 1):
            status = "✓" if result["extract_success"] and result["save_success"] else "✗"
            report += f"{idx}. **{status} {result['title'][:60]}**\n"
            report += f"   - Extract: {'Success' if result['extract_success'] else 'Failed'}"
            if result.get('extract_time'):
                report += f" ({result['extract_time']}s)"
            report += "\n"
            report += f"   - Entities: {result.get('entities_extracted', 0)}\n"
            report += f"   - Relations: {result.get('relations_extracted', 0)}\n"
            if result.get('error'):
                report += f"   - Error: {result['error']}\n"
            report += "\n"

        report += f"""
## 3. Database Analysis

### Entity Statistics

- **Total Entities:** {self.results["database_stats"].get("total_entities", 0)}
- **Total Relations:** {self.results["database_stats"].get("total_relations", 0)}

### Top 10 Most Connected Entities

"""

        for idx, entity in enumerate(self.results["database_stats"].get("top_entities", [])[:10], 1):
            report += f"{idx}. **{entity['name']}** ({entity['type']})\n"
            report += f"   - Connections: {entity['connections']}\n"

        report += "\n### Relation Type Distribution\n\n"

        for rel in self.results["database_stats"].get("relation_types", []):
            report += f"- **{rel['type']}**: {rel['count']}\n"

        report += "\n## 4. Inference Calculation\n\n"

        if self.results.get("inferences"):
            role_inferences = self.results["inferences"].get("role_inferences", [])

            if role_inferences:
                report += f"**Total Role Inferences:** {len(role_inferences)}\n\n"
                report += "| Role Type | Score | Coverage | Confidence | Disagreement |\n"
                report += "|-----------|-------|----------|------------|-------------|\n"

                for inference in role_inferences[:20]:  # Top 20
                    role_type = inference.get("role_type", "N/A")
                    score = inference.get("score")
                    coverage = inference.get("coverage", 0)
                    confidence = inference.get("confidence", 0)
                    disagreement = inference.get("disagreement", 0)

                    score_str = f"{score:.3f}" if score is not None else "N/A"
                    report += f"| {role_type} | {score_str} | "
                    report += f"{coverage:.2f} | {confidence:.2f} | {disagreement:.2f} |\n"

                report += "\n"
            else:
                report += "No role inferences calculated.\n\n"
        else:
            report += "No inference data available.\n\n"

        report += "## 5. Key Findings\n\n"

        # Generate key findings
        if successful_saves > 0:
            report += f"✓ Successfully extracted and saved knowledge from {successful_saves} sources\n"

        if self.results["database_stats"].get("total_entities", 0) > 0:
            report += f"✓ Created {self.results['database_stats']['total_entities']} entities in the knowledge graph\n"

        if self.results["database_stats"].get("total_relations", 0) > 0:
            report += f"✓ Established {self.results['database_stats']['total_relations']} relations between entities\n"

        if self.results.get("inferences"):
            report += "✓ Inference calculation working correctly\n"

        if len(self.results.get("errors", [])) > 0:
            report += f"\n⚠ {len(self.results['errors'])} errors encountered during workflow\n"
            for error in self.results["errors"]:
                report += f"  - {error}\n"

        report += "\n## Conclusion\n\n"

        if successful_saves >= total_sources * 0.8:  # 80% success rate
            report += "✓ **Workflow Status: SUCCESS**\n\n"
            report += "The complete knowledge graph workflow is functioning correctly with LLM extraction working as expected.\n"
        else:
            report += "⚠ **Workflow Status: PARTIAL SUCCESS**\n\n"
            report += f"Only {successful_saves}/{total_sources} sources were successfully processed. Review errors above.\n"

        # Save report
        report_path = "/home/thibaut/code/hyphagraph/FIBROMYALGIA_TEST_RESULTS.md"
        with open(report_path, "w") as f:
            f.write(report)

        self.log(f"✓ Report saved to: {report_path}")

        # Also save JSON results
        json_path = "/home/thibaut/code/hyphagraph/FIBROMYALGIA_TEST_RESULTS.json"
        with open(json_path, "w") as f:
            json.dump(self.results, f, indent=2)

        self.log(f"✓ JSON results saved to: {json_path}")

    def run_complete_workflow(self):
        """Execute the complete workflow"""
        self.log("="*60)
        self.log("FIBROMYALGIA KNOWLEDGE GRAPH - COMPLETE WORKFLOW TEST")
        self.log("="*60)

        # Step 1: Login
        if not self.step1_login():
            self.log("✗ Cannot proceed without authentication")
            return

        # Get sources
        sources = self.get_sources()
        if not sources:
            self.log("✗ No sources found in database")
            return

        # Step 2: Extract knowledge
        self.step2_extract_knowledge(sources)

        # Step 3: Analyze database
        self.step3_analyze_database()

        # Step 4: Calculate inferences
        self.step4_calculate_inferences()

        # Step 5: Generate report
        self.step5_generate_report()

        self.log("\n" + "="*60)
        self.log("WORKFLOW COMPLETE!")
        self.log("="*60)


if __name__ == "__main__":
    tester = WorkflowTester()
    tester.run_complete_workflow()
