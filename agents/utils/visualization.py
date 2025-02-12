from py2neo import Graph as py2neo_Graph
import networkx as nx
from pyvis.network import Network
from IPython.display import IFrame, display
from datetime import datetime
import os


def visualize_neo4j_results_v1(result_dict,html_filename = "visualize_graph.html"):
    """
    Updated function to handle:
      1) 'Graph-style' returns (e.g. RETURN p, a, r or RETURN n, r, p).
      2) 'Tabular-style' returns, even if they only return a single column.

    Now includes a case for (p, prog) to represent :SANCTIONED_BY relationships.

    Example usage:
      # Case A: Graph-style query
      MATCH (p:Person)-[r:HAS_ALIAS]->(a:Alias)
      WHERE a.firstName = 'Muhammad' AND a.lastName = 'ZAYDAN'
      RETURN p, a, r

      # Case B: Also works if you return just two nodes:
      MATCH (p:Person)-[:HAS_ALIAS]->(a:Alias)
      WHERE a.firstName = 'Muhammad' AND a.lastName = 'ZAYDAN'
      RETURN p, a

      # Case C: Single-column query
      MATCH (p:Person)-[:HAS_ALIAS]->(a:Alias)
      WHERE a.firstName = 'Muhammad' AND a.lastName = 'ZAYDAN'
      RETURN a.fullname AS Alias

      # Case D: Person sanctioned by program
      MATCH (p:Person)-[s:SANCTIONED_BY]->(prog:Program)
      WHERE prog.name IN ['SDGT']
      RETURN p, s, prog

    NOTE: If you want to see the relationship drawn, you must return at least two nodes 
    or provide enough columns for the code to infer a relationship. 
    A single column of strings doesn't contain relationship info.
    """

    # Extract the list of records
    cypher_result = result_dict.get("cypher_result", [])
    
    net = Network(height='600px', width='100%', bgcolor='#ffffff', font_color='black', directed=True)

    color_map = {
        'Person': '#F9C6CD',            # Light pink
        'Alias': '#7DB37D',             # Sage green
        'Address': '#E8935A',           # Coral orange
        'Program': '#E57C9C',           # Pink rose
        'Identitydocument': '#4C8FBD',  # Blue
        'Unknown': '#cccccc'
    }

    added_nodes = set()
    added_edges = set()

    def guess_node_type(props):
        # Simple heuristic based on known fields
        if 'entitytype' in props or 'birthdate' in props or 'fullName' in props:
            return 'Person'
        if 'documentnumber' in props and 'type' in props:
            return 'Identitydocument'
        if 'fullname' in props and ('firstName' in props or 'lastName' in props):
            return 'Alias'
        if 'country' in props or 'city' in props or 'address' in props:
            return 'Address'
        if 'name' in props:
            return 'Program'
        return 'Unknown'

    def build_title(label, props):
        lines = [f"{label}:"]
        for k, v in props.items():
            lines.append(f"{k}: {v}")
        return "\n".join(lines)

    def add_node(node_id, label, props):
        if node_id not in added_nodes:
            title = build_title(label, props)
            net.add_node(
                node_id,
                label=label,
                title=title,
                color=color_map.get(label, '#cccccc')
            )
            added_nodes.add(node_id)

    def add_edge(src_id, dst_id, rel_type):
        edge_key = f"{src_id}-{dst_id}-{rel_type}"
        if edge_key not in added_edges:
            net.add_edge(
                src_id,
                dst_id,
                title=rel_type,
                label=rel_type,
                arrows='to'
            )
            added_edges.add(edge_key)

    # Iterate over each record in cypher_result
    for record in cypher_result:
        # 1) Check "graph style" => if "n", "p", "r"
        if ("n" in record and "p" in record and "r" in record):
            n_data = record["n"]
            p_data = record["p"]
            r_tuple = record["r"]
            if len(r_tuple) == 3:
                # r_tuple = (startNodeProps, relationshipName, endNodeProps)
                relationship_type = r_tuple[1]
                # Person node (just a guess if 'p' is the Person)
                p_id = p_data.get("id") or p_data.get("fullName") or "PersonNode"
                add_node(p_id, "Person", p_data)
                # Other node
                n_type = guess_node_type(n_data)
                n_id = n_data.get("id") or n_data.get("name") or "NodeWithoutID"
                add_node(n_id, n_type, n_data)
                # Edge
                add_edge(p_id, n_id, relationship_type)

        # 2) If "p" and "a" are both nodes => Person & Alias
        elif ("p" in record and "a" in record):
            p_data = record["p"]
            a_data = record["a"]
            p_id = p_data.get("id") or p_data.get("fullName") or "PersonNode"
            add_node(p_id, "Person", p_data)
            a_type = guess_node_type(a_data)
            a_id = a_data.get("id") or a_data.get("fullname") or "AliasNode"
            add_node(a_id, a_type, a_data)
            add_edge(p_id, a_id, "HAS_ALIAS")

        # 3) If "p" and "d" are both nodes => Person & Document
        elif ("p" in record and "d" in record):
            p_data = record["p"]
            d_data = record["d"]
            p_id = p_data.get("id") or p_data.get("fullName") or "PersonNode"
            add_node(p_id, "Person", p_data)
            d_type = guess_node_type(d_data)
            d_id = d_data.get("id") or d_data.get("documentnumber") or "DocNode"
            add_node(d_id, d_type, d_data)
            add_edge(p_id, d_id, "HAS_DOCUMENT")

        # 4) If "p" and "prog" => Person & Program (SANCTIONED_BY)
        elif ("p" in record and "prog" in record):
            p_data = record["p"]
            prog_data = record["prog"]
            p_id = p_data.get("id") or p_data.get("fullName") or "PersonNode"
            add_node(p_id, "Person", p_data)
            prog_type = guess_node_type(prog_data)
            prog_id = prog_data.get("id") or prog_data.get("name") or "ProgramNode"
            add_node(prog_id, prog_type, prog_data)
            add_edge(p_id, prog_id, "SANCTIONED_BY")

        # 5) Single-column "Alias"
        elif "Alias" in record and len(record) == 1:
            alias_str = record["Alias"]
            add_node(alias_str, "Alias", {"fullname": alias_str})

        # 6) If it's the "p.fullName, d.type, d.documentNumber" style
        elif ("fullName" in record and "documentType" in record and "documentNumber" in record):
            full_name = record["fullName"]
            doc_type = record["documentType"]
            doc_num = record["documentNumber"]

            # Person
            p_id = full_name
            add_node(p_id, "Person", {"fullName": full_name})

            # Document
            doc_id = f"{doc_type}_{doc_num}"
            add_node(doc_id, "Identitydocument", {"type": doc_type, "documentnumber": doc_num})
            add_edge(p_id, doc_id, "HAS_DOCUMENT")

        else:
            # Catch-all: If there's some other structure, handle or skip as needed.
            pass

    # Network options
    net.set_options("""
    var options = {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "springLength": 100,
                "springConstant": 0.08
            },
            "solver": "forceAtlas2Based",
            "minVelocity": 0.75
        },
        "edges": {
            "font": {
                "size": 8,
                "align": "middle"
            },
            "smooth": false
        },
        "nodes": {
            "font": {
                "size": 12
            }
        }
    }
    """)

    cypher_query = result_dict.get("generated_cypher", "No query provided")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # metadata_html = f"""
    # <div style="position: fixed; top: 10px; right: 10px; background: rgba(255,255,255,0.9); 
    #             padding: 10px; border-radius: 5px; border: 1px solid #ccc; max-width: 500px; 
    #             font-family: monospace; font-size: 12px;">
    #     <strong>Generated:</strong> {timestamp}<br>
    #     <strong>Cypher Query:</strong><br>
    #     <pre style="margin: 5px 0; white-space: pre-wrap;">{cypher_query}</pre>
    # </div>
    # """

    metadata_html = f"""
    <div style="position: fixed; top: 10px; right: 10px; background: rgba(255,255,255,0.9); 
            padding: 5px 10px; border-radius: 5px; border: 1px solid #ccc; 
            font-family: monospace; font-size: 12px;">
    <strong>Generated:</strong> {timestamp}
    </div>
    """

    # Write to HTML and return the IFrame
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        html_path = os.path.join(parent_dir, html_filename)
        
        print(f"Saving graph: {html_path}")
        net.write_html(html_path)

        # Insert metadata into the generated HTML
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Insert metadata div before the closing body tag
        content = content.replace('</body>', f'{metadata_html}</body>')
        
        # Return the HTML content directly
        return content

    except Exception as e:
        print(f"Error saving graph: {e}")
        return None
    

from pyvis.network import Network
from datetime import datetime
import os

def visualize_neo4j_results_v2(result_dict, html_filename="visualize_graph.html"):
    """
    A more flexible visualization function that can handle various Cypher query patterns.
    
    Args:
        result_dict: Dictionary containing:
            - cypher_result: List of dictionaries with query results
            - generated_cypher: The Cypher query that was executed
        html_filename: Name of the output HTML file
    
    Returns:
        str: HTML content for the visualization
    """
    cypher_result = result_dict.get("cypher_result", [])
    
    net = Network(height='600px', width='100%', bgcolor='#ffffff', font_color='black', directed=True)

    # Color scheme for different node types
    color_map = {
        'Person': '#F9C6CD',            # Light pink
        'Alias': '#7DB37D',             # Sage green
        'Address': '#E8935A',           # Coral orange
        'Program': '#E57C9C',           # Pink rose
        'Identitydocument': '#4C8FBD',  # Blue
        'Unknown': '#cccccc'            # Gray for unknown types
    }

    added_nodes = set()
    added_edges = set()

    
    def guess_node_type(props):
        """Guess the node type based on its properties"""
        if not props:
            return 'Unknown'
        
        # Convert keys to lowercase for case-insensitive matching
        props_lower = {k.lower(): v for k, v in props.items()}
        
        # Check for Alias first to prevent misclassification
        if 'fullname' in props_lower and not props_lower.get('entitytype'):
            return 'Alias'
        
        if 'entitytype' in props_lower or 'birthdate' in props_lower:
            return 'Person'
        if 'documentnumber' in props_lower:
            return 'Identitydocument'
        if any(key in ['country', 'city', 'address'] for key in props_lower):
            return 'Address'
        if 'name' in props_lower:
            return 'Program'
        return 'Unknown'

    def add_node(node_data):
        """Add a node to the network if it hasn't been added yet"""
        if not node_data:
            return None
            
        # Get node ID
        node_id = node_data.get('id') or node_data.get('fullName') or node_data.get('fullname') or str(node_data)
        
        if node_id not in added_nodes:
            node_type = guess_node_type(node_data)
            
            # Build node label based on type
            if node_type == 'Identitydocument':
                # For identity documents, show type and number
                label = f"{node_data.get('type', 'Document')}\n{node_data.get('documentnumber', '')}"
            elif node_type == 'Person':
                # For persons, show "Person" text and full name
                full_name = node_data.get('fullName') or node_data.get('firstName', '') + ' ' + node_data.get('lastName', '')
                label = f"Person\n{full_name}"
            elif node_type == 'Alias':
                # For aliases, show "Alias" text and full name
                alias_name = node_data.get('fullname') or node_data.get('firstName', '') + ' ' + node_data.get('lastName', '')
                label = f"Alias\n{alias_name}"
            elif node_type == 'Program':
                # For programs, show the program name
                label = node_data.get('name', 'Program')
            else:
                label = str(node_id)
            
            # Build tooltip content
            tooltip = "\n".join(f"{k}: {v}" for k, v in node_data.items())
            
            net.add_node(
                node_id,
                label=label,
                title=tooltip,
                color=color_map.get(node_type, color_map['Unknown'])
            )
            added_nodes.add(node_id)
        
        return node_id

    def add_edge(source_id, target_id, rel_type=""):
        """Add an edge to the network if it hasn't been added yet"""
        if not (source_id and target_id):
            return
            
        edge_key = f"{source_id}-{target_id}-{rel_type}"
        if edge_key not in added_edges:
            net.add_edge(
                source_id,
                target_id,
                title=rel_type,
                label=rel_type,
                arrows='to'
            )
            added_edges.add(edge_key)

    def process_record(record):
        """Process a single record from the query result"""
        nodes_to_process = []
        edges_to_add = []
        
        # First pass: collect all node data
        for key, value in record.items():
            if isinstance(value, (dict, list, tuple)):
                if isinstance(value, (list, tuple)) and len(value) == 3:
                    # This might be a relationship tuple (start_node, rel_type, end_node)
                    nodes_to_process.extend([value[0], value[2]])
                    edges_to_add.append((value[0], value[2], value[1]))
                else:
                    nodes_to_process.append(value)
        
        # Second pass: add nodes
        node_ids = {}
        for node_data in nodes_to_process:
            if isinstance(node_data, dict):
                node_id = add_node(node_data)
                if node_id:
                    node_ids[str(node_data)] = node_id
        
        # Third pass: add edges
        for start_node, end_node, rel_type in edges_to_add:
            start_id = node_ids.get(str(start_node))
            end_id = node_ids.get(str(end_node))
            if isinstance(rel_type, str):
                rel_name = rel_type
            else:
                rel_name = str(rel_type)
            add_edge(start_id, end_id, rel_name)

    # Process all records
    for record in cypher_result:
        process_record(record)

    # Add physics options for better layout
    net.set_options("""
    var options = {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "springLength": 100,
                "springConstant": 0.08
            },
            "solver": "forceAtlas2Based",
            "minVelocity": 0.75
        },
        "edges": {
            "font": {
                "size": 8,
                "align": "middle"
            },
            "smooth": false
        },
        "nodes": {
            "font": {
                "size": 12
            }
        }
    }
    """)

    # Add metadata (timestamp and query)
    cypher_query = result_dict.get("generated_cypher", "No query provided")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    metadata_html = f"""
    <div style="position: fixed; top: 10px; right: 10px; background: rgba(255,255,255,0.9); 
            padding: 5px 10px; border-radius: 5px; border: 1px solid #ccc; 
            font-family: monospace; font-size: 12px;">
    <strong>Generated:</strong> {timestamp}
    </div>
    """

    try:
        # Save to HTML file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        html_path = os.path.join(parent_dir, html_filename)
        
        print(f"Saving graph: {html_path}")
        net.write_html(html_path)

        # Add metadata to HTML
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.replace('</body>', f'{metadata_html}</body>')
        
        return content

    except Exception as e:
        print(f"Error saving graph: {e}")
        return None