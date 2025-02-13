
//Show schema
call db.schema.visualization()

//Show sameples
MATCH (n)
RETURN (n);

//Connections more than 10
MATCH (p:Person)-[r]-()
WITH p, COUNT(r) AS connections
WHERE connections >= 10
RETURN p, connections
ORDER BY connections DESC;

// Connections more than 10 in details
MATCH (p:Person)-[r]-(n)
WITH p, COUNT(r) AS connections, COLLECT(n) AS connected_nodes
WHERE connections >= 10
RETURN p, connections, connected_nodes
ORDER BY connections DESC;

// Search by Alias
MATCH (alias:Alias)-[:HAS_ALIAS]-(p:Person)
WHERE toLower(alias.firstName) CONTAINS toLower("SALIM")
   OR toLower(alias.lastName) CONTAINS toLower("SALIM")
MATCH (n)-[r]-(p)
RETURN n, r, p;

// Search by Name
MATCH (alias:Alias)-[:HAS_ALIAS]-(p:Person)
WHERE toLower(p.firstName) CONTAINS toLower("Ayman")
   OR toLower(p.lastName) CONTAINS toLower("Ayman")
MATCH (n)-[r]-(p)
RETURN n, r, p;

//Show all paths of 2 Person
MATCH path = (p1:Person)-[*]-(p2:Person)
WHERE p1.id = "2675" AND p2.id = "2691"
RETURN path;


//Show all people that connected
MATCH (p:Person)
WITH p
MATCH path = (p)-[*]-(connectedPerson:Person)
RETURN path;


//Show everything of one person
MATCH (n)-[r]-(p:Person) WHERE p.id = "2676" RETURN n, r, p


//Show person with 5 alias
MATCH (p:Person)-[:HAS_ALIAS]->(a:Alias)
WITH p, COUNT(a) AS alias_count
WHERE alias_count = 5
RETURN p, alias_count;


//Show shorted path of 2 Person
MATCH path = shortestPath((p1:Person)-[*]-(p2:Person))
WHERE p1.id = "2675" AND p2.id = "2691"
RETURN path;


// Syndicates
MATCH (p:Person)
WITH p
MATCH path = (p)-[*]-(connectedPerson:Person)
WITH p, COLLECT(DISTINCT connectedPerson) AS group
RETURN group;


// DELETE everything!!
MATCH (n)
DETACH DELETE n;