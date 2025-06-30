import asyncio
import structlog
from neo4j import AsyncGraphDatabase
from app.config import settings

logger = structlog.get_logger()


class Neo4jInitializer:
    """Inicializador automático do schema Neo4j"""
    
    def __init__(self):
        self.driver = None
    
    async def initialize_database(self):
        """Inicializa o banco de dados Neo4j com schema completo"""
        try:
            # Conecta ao Neo4j
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            
            logger.info("🔗 Connecting to Neo4j for schema initialization...")
            
            # Executa inicialização do schema
            await self._create_constraints()
            await self._create_sample_data()
            await self._create_indexes()
            
            logger.info("✅ Neo4j schema initialized successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Neo4j schema: {e}")
            raise
        finally:
            if self.driver:
                await self.driver.close()
    
    async def _create_constraints(self):
        """Cria constraints únicos"""
        constraints = [
            # Constraints para nós únicos
            "CREATE CONSTRAINT person_userid IF NOT EXISTS FOR (p:Person) REQUIRE p.userID IS UNIQUE",
            "CREATE CONSTRAINT organization_name IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE",
            "CREATE CONSTRAINT system_name IF NOT EXISTS FOR (s:System) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT location_name IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE",
            "CREATE CONSTRAINT role_name IF NOT EXISTS FOR (r:Role) REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT product_name IF NOT EXISTS FOR (pr:Product) REQUIRE pr.name IS UNIQUE",
            "CREATE CONSTRAINT event_name IF NOT EXISTS FOR (e:Event) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT issue_id IF NOT EXISTS FOR (i:Issue) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT goal_id IF NOT EXISTS FOR (g:Goal) REQUIRE g.id IS UNIQUE",
            
            # Constraints para memórias
            "CREATE CONSTRAINT user_memory_id IF NOT EXISTS FOR (m:UserMemory) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT session_memory_id IF NOT EXISTS FOR (m:SessionMemory) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT company_memory_id IF NOT EXISTS FOR (m:CompanyMemory) REQUIRE m.id IS UNIQUE"
        ]
        
        async with self.driver.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                    logger.debug(f"✓ Constraint created: {constraint.split()[-3]}")
                except Exception as e:
                    if "already exists" not in str(e):
                        logger.warning(f"⚠️ Constraint failed: {e}")
    
    async def _create_sample_data(self):
        """Cria dados de exemplo para definir o schema"""
        sample_queries = [
            # Pessoa de exemplo
            """
            MERGE (p:Person {
                userID: "system_init",
                name: "Sistema",
                type: "system_user"
            })
            """,
            
            # Organização de exemplo
            """
            MERGE (o:Organization {
                name: "Sil Sistemas",
                type: "company",
                description: "Empresa de desenvolvimento de software"
            })
            """,
            
            # Sistema de exemplo
            """
            MERGE (s:System {
                name: "AQX",
                type: "management_system",
                description: "Sistema de gestão para abatedouros"
            })
            """,
            
            # Localização de exemplo
            """
            MERGE (l:Location {
                name: "Brasil",
                type: "country",
                description: "País"
            })
            """,
            
            # Papel/Função de exemplo
            """
            MERGE (r:Role {
                name: "Desenvolvedor",
                type: "job_title",
                description: "Função de desenvolvimento de software"
            })
            """,
            
            # Conceito de exemplo
            """
            MERGE (c:Concept {
                name: "Gestão de Abatedouros",
                type: "business_concept",
                description: "Conceito de negócio relacionado ao gerenciamento de abatedouros"
            })
            """,
            
            # Produto de exemplo
            """
            MERGE (pr:Product {
                name: "Software AQX",
                type: "software_product",
                description: "Produto de software para gestão"
            })
            """,
            
            # Issue de exemplo
            """
            MERGE (i:Issue {
                id: "sample_issue",
                description: "Problema de exemplo",
                type: "technical_issue",
                status: "resolved"
            })
            """,
            
            # Goal de exemplo
            """
            MERGE (g:Goal {
                id: "sample_goal",
                description: "Objetivo de exemplo",
                type: "business_goal",
                status: "active"
            })
            """,
            
            # Memória de exemplo
            """
            MERGE (m:UserMemory:Memory {
                id: "sample_memory",
                user_id: "system_init",
                question: "Como funciona o sistema?",
                answer: "O sistema funciona de forma integrada",
                timestamp: datetime(),
                embedding: [0.1, 0.2, 0.3, 0.4, 0.5]
            })
            """,
            
            # Relacionamentos de exemplo
            """
            MATCH (p:Person {userID: "system_init"})
            MATCH (o:Organization {name: "Sil Sistemas"})
            MERGE (p)-[:WORKS_AT {
                valid_at: datetime(),
                type: "employment",
                status: "active"
            }]->(o)
            """,
            
            """
            MATCH (p:Person {userID: "system_init"})
            MATCH (s:System {name: "AQX"})
            MERGE (p)-[:USES {
                valid_at: datetime(),
                purpose: "desenvolvimento",
                frequency: "daily"
            }]->(s)
            """,
            
            """
            MATCH (o:Organization {name: "Sil Sistemas"})
            MATCH (s:System {name: "AQX"})
            MERGE (o)-[:DEVELOPS {
                valid_at: datetime(),
                type: "software_development"
            }]->(s)
            """,
            
            """
            MATCH (p:Person {userID: "system_init"})
            MATCH (c:Concept {name: "Gestão de Abatedouros"})
            MERGE (p)-[:KNOWS_ABOUT {
                valid_at: datetime(),
                level: "expert"
            }]->(c)
            """
        ]
        
        async with self.driver.session() as session:
            for query in sample_queries:
                try:
                    await session.run(query)
                    logger.debug("✓ Sample data created")
                except Exception as e:
                    logger.warning(f"⚠️ Sample data creation failed: {e}")
    
    async def _create_indexes(self):
        """Cria índices para melhor performance"""
        indexes = [
            "CREATE INDEX person_name_idx IF NOT EXISTS FOR (p:Person) ON (p.name)",
            "CREATE INDEX organization_type_idx IF NOT EXISTS FOR (o:Organization) ON (o.type)",
            "CREATE INDEX system_type_idx IF NOT EXISTS FOR (s:System) ON (s.type)",
            "CREATE INDEX memory_user_idx IF NOT EXISTS FOR (m:UserMemory) ON (m.user_id)",
            "CREATE INDEX memory_timestamp_idx IF NOT EXISTS FOR (m:UserMemory) ON (m.timestamp)"
        ]
        
        async with self.driver.session() as session:
            for index in indexes:
                try:
                    await session.run(index)
                    logger.debug(f"✓ Index created: {index.split()[2]}")
                except Exception as e:
                    if "already exists" not in str(e):
                        logger.warning(f"⚠️ Index creation failed: {e}")


# Função helper para executar inicialização
async def initialize_neo4j_schema():
    """Função helper para inicializar o schema Neo4j"""
    initializer = Neo4jInitializer()
    await initializer.initialize_database()


# Para executar diretamente
if __name__ == "__main__":
    asyncio.run(initialize_neo4j_schema())
