from py2neo import Graph as py2neo_Graph
import networkx as nx
from pyvis.network import Network
from IPython.display import IFrame, display
from datetime import datetime


def visualize_neo4j_query(query, uri, user, password):
    """
    Creates an interactive visualization of Neo4j query results
    """
    
    # Connect to Neo4j
    vgraph = py2neo_Graph(uri, auth=(user, password))
    
    # Execute the query
    results = vgraph.run(query)
    
    # Create a NetworkX graph
    G = nx.DiGraph()
    
    # Add nodes and edges to the NetworkX graph
    for record in results:
        n = record['n']
        m = record['m']
        r = record['r']
        
        # Get only string-serializable properties
        n_id = str(n.identity)
        m_id = str(m.identity)
        
        # Get node labels and properties
        n_label = list(n.labels)[0]
        m_label = list(m.labels)[0]
        
        # Create display names based on node type
        if n_label == "Person":
            n_display = dict(n).get("fullName", "")
        elif n_label == "Program":
            n_display = dict(n).get("name", "")
        else:
            n_display = str(dict(n))
            
        if m_label == "Person":
            m_display = dict(m).get("fullName", "")
        elif m_label == "Program":
            m_display = dict(m).get("name", "")
        else:
            m_display = str(dict(m))
        
        # Add nodes with custom display names
        G.add_node(n_id, title=n_display, label=n_label)
        G.add_node(m_id, title=m_display, label=m_label)
        
        # Add edge with relationship type as the title
        G.add_edge(n_id, m_id, title=str(r.type))
    
    # Create and configure the network
    net = Network(
        height='600px', 
        width='100%',
        bgcolor='#ffffff',
        font_color='black',
        directed=True
    )
    
    # Color mapping for different node types
    color_map = {
        'Person': '#F9C6CD',
        'Alias': '#7DB37D',
        'Identitydocument': '#4C8FBD',
        'Program': '#E57C9C',
        'Address': '#E8935A'
    }
    
    # Add the nodes with color coding
    for node, node_attrs in G.nodes(data=True):
        label = node_attrs.get('label', '')
        color = color_map.get(label, '#808080')
        
        title = node_attrs.get('title', '')
        if not isinstance(title, str):
            title = str(title)
            
        net.add_node(
            str(node),
            label=str(label),
            title=title,
            color=color
        )
    
    # Add the edges with relationship types
    for edge in G.edges():
        source, target = edge
        edge_data = G.get_edge_data(source, target)
        title = edge_data.get('title', '')
        if not isinstance(title, str):
            title = str(title)
            
        net.add_edge(
            str(source),
            str(target),
            title=title,
            arrows='to'
        )
    
    # Save and display
    try:
        # Use save_graph instead of write_html
        net.save_graph("neo4j_graph_1.html")
        return IFrame("neo4j_graph_1.html", width=800, height=600)
    except Exception as e:
        print(f"Error saving graph: {str(e)}")
        return None
    
def visualize_neo4j_results(result_dict):
    """
    Updated function to handle:
      1) 'Graph-style' returns (e.g. RETURN p, a, or RETURN n, r, p).
      2) 'Tabular-style' returns, even if they only return a single column.

    If the query returns only a single column of strings (e.g. a.fullname AS Alias),
    we can only display standalone nodes (no relationships). 

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

    NOTE: If you want to see the relationship drawn, you must return at least two nodes 
    or provide enough columns for the code to infer a relationship. 
    A single column of strings doesn't contain relationship info.
    """

    # Extract the list of records
    cypher_result = result_dict.get("cypher_result", [])
    
    net = Network(height='600px', width='100%', bgcolor='#ffffff', font_color='black', directed=True)

    color_map = {
        'Person': '#F9C6CD',
        'Alias': '#7DB37D',
        'Identitydocument': '#4C8FBD',
        'Program': '#E57C9C',
        'Address': '#E8935A',
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

    for record in cypher_result:
        # 1) Check "graph style" => if "n", "p", "r" or other node keys are present
        #    Example: { "n": {...}, "p": {...}, "r": (startNode, relName, endNode) }
        if ("n" in record and "p" in record and "r" in record):
            # "n", "p", and "r" approach
            n_data = record["n"]
            p_data = record["p"]
            r_tuple = record["r"]
            if len(r_tuple) == 3:
                # r_tuple = (startNodeProps, relationshipName, endNodeProps)
                relationship_type = r_tuple[1]
                # Person node
                p_id = p_data.get("id") or p_data.get("fullName") or "PersonNode"
                add_node(p_id, "Person", p_data)
                # Other node
                n_type = guess_node_type(n_data)
                n_id = n_data.get("id") or n_data.get("name") or "NodeWithoutID"
                add_node(n_id, n_type, n_data)
                # Edge
                add_edge(p_id, n_id, relationship_type)

        # 2) If "p" and "a" are both nodes, with or without "r"
        elif ("p" in record and "a" in record):
            p_data = record["p"]
            a_data = record["a"]
            # Person
            p_id = p_data.get("id") or p_data.get("fullName") or "PersonNode"
            add_node(p_id, "Person", p_data)
            # Alias (or other node)
            a_type = guess_node_type(a_data)
            a_id = a_data.get("id") or a_data.get("fullname") or "AliasNode"
            add_node(a_id, a_type, a_data)
            # Typically, that means there's a :HAS_ALIAS relationship
            add_edge(p_id, a_id, "HAS_ALIAS")

        # 3) If "p" and "d" are both nodes (like Person + Document)
        elif ("p" in record and "d" in record):
            p_data = record["p"]
            d_data = record["d"]
            # Person
            p_id = p_data.get("id") or p_data.get("fullName") or "PersonNode"
            add_node(p_id, "Person", p_data)
            # Identitydocument
            d_type = guess_node_type(d_data)
            d_id = d_data.get("id") or d_data.get("documentnumber") or "DocNode"
            add_node(d_id, d_type, d_data)
            # Typically, that's :HAS_DOCUMENT
            add_edge(p_id, d_id, "HAS_DOCUMENT")

        # 4) If you have a single column like "Alias" -> we create a single node
        #    (No relationship info)
        elif "Alias" in record and len(record) == 1:
            alias_str = record["Alias"]
            add_node(alias_str, "Alias", {"fullname": alias_str})

        # 5) If it's the "p.fullName, d.type, d.documentNumber" style => let's detect that
        elif ("fullName" in record and "documentType" in record and "documentNumber" in record):
            # Person -> Document
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
            # Catch-all: If there's some other structure, you can decide how to handle it here
            # For a single column of strings (with a different name), or multiple columns,
            # you'd write logic to parse them. But there's no universal approach for every case,
            # because different queries can return drastically different shapes.
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

    # Write to HTML and return the IFrame
    try:
       
        html_filename = "neo4j_graph_2.html"
        print(f"Saving graph:{html_filename}")
        net.write_html(html_filename)
        return IFrame(html_filename, width=800, height=600)
    except Exception as e:
        print(f"Error saving graph: {e}")
        return None
    


def visualize_neo4j_results_optimized(result_dict,html_filename = "visualize_graph.html"):
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

    metadata_html = f"""
    <div style="position: fixed; top: 10px; right: 10px; background: rgba(255,255,255,0.9); 
                padding: 10px; border-radius: 5px; border: 1px solid #ccc; max-width: 500px; 
                font-family: monospace; font-size: 12px;">
        <strong>Generated:</strong> {timestamp}<br>
        <strong>Cypher Query:</strong><br>
        <pre style="margin: 5px 0; white-space: pre-wrap;">{cypher_query}</pre>
    </div>
    """

    # Write to HTML and return the IFrame
    try:
        
        print(f"Saving graph: {html_filename}")
        net.write_html(html_filename)

        # Insert metadata into the generated HTML
        with open(html_filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Insert metadata div before the closing body tag
        content = content.replace('</body>', f'{metadata_html}</body>')
        
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(content)

        return IFrame(html_filename, width=800, height=600)
    except Exception as e:
        print(f"Error saving graph: {e}")
        return None
