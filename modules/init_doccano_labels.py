import os
import requests
import logging
from doccano_client import DoccanoClient
from dotenv import load_dotenv
load_dotenv()
from util.config_util import ConfigUtil
config = ConfigUtil.get_config()

# Configuración Base
BASE_URL = os.getenv("DOCCANO_URL")
ADMIN_USER = os.getenv("DOCCANO_USERNAME")
ADMIN_PASS = os.getenv("DOCCANO_PASSWORD")
PROJECT_ID = config.main.project_id
COMMON_PASSWORD = os.getenv("DOCCANO_COMMON_PASSWORD")
exclude_list = config.init_doccano_labels.exclude_members

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def discover_token_endpoint(username, password):
    """Prueba múltiples endpoints de Doccano para encontrar el correcto."""
    endpoints = [
        "/v1/auth-token/",
        "/v1/auth/login/",
        "/auth-token/",
        "/api-token-auth/",
        "/v1/api-token-auth/"
    ]
    
    for ep in endpoints:
        url = f"{BASE_URL}{ep}"
        try:
            logger.info(f"Probando autenticación en: {url}")
            response = requests.post(url, json={'username': username, 'password': password}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('token') or data.get('key') or data.get('auth_token')
                if token:
                    logger.info(f"¡Éxito! Token encontrado en {ep}")
                    return token
            else:
                logger.warning(f"Respuesta {response.status_code} en {ep}: {response.text[:100]}")
        except Exception as e:
            logger.error(f"Error de conexión en {ep}: {e}")
            
    return None

def get_examples_manually(token):
    examples = []
    # Iniciamos con la URL base correcta y el puerto
    url = f"{BASE_URL}/v1/projects/{PROJECT_ID}/examples"
    headers = {'Authorization': f'Token {token}'}
    
    while url:
        # LOGICA DE LIMPIEZA DE URL (Crucial para tu servidor)
        # Si la URL viene sin el puerto 8080, se lo inyectamos
        if "8080" not in url:
            # Reemplazamos el host por el BASE_URL completo
            if "/v1/" in url:
                path = url.split("/v1/")[-1]
                url = f"{BASE_URL}/v1/{path}"
            else:
                # Caso genérico por si cambia la estructura
                import re
                url = re.sub(r'http://[0-9.]+/', f'{BASE_URL}/', url)

        logger.info(f"Consultando página: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            examples.extend(data['results'])
            url = data['next'] # Aquí el servidor te manda la URL malformada sin puerto
            
            logger.info(f"Acumulados: {len(examples)} ejemplos.")
        except Exception as e:
            logger.error(f"Error al consultar la API: {e}")
            break
            
    return examples

def replicate_everything():
    # 1. Descubrimiento de Token
    token = discover_token_endpoint(ADMIN_USER, ADMIN_PASS)
    if not token:
        logger.error("No se pudo obtener el token tras probar todos los endpoints conocidos.")
        return

    # 2. Inicializar clientes
    admin_client = DoccanoClient(BASE_URL)
    admin_client.login(username=ADMIN_USER, password=ADMIN_PASS)
    
    # 3. Obtener ejemplos
    examples_data = get_examples_manually(token)
    
    # 4. Miembros del proyecto
    exclude_list = config.init_doccano_labels.exclude_members
    project_members = [u for u in admin_client.list_members(PROJECT_ID) if u.username != ADMIN_USER and u.username not in exclude_list]    
    
    for user in project_members:
        logger.info(f"--- Iniciando: {user.username} ---")
        try:
            user_client = DoccanoClient(BASE_URL)
            user_client.login(username=user.username, password=COMMON_PASSWORD)
            
            for ex in examples_data:
                ex_id = ex['id']
                orig_spans = admin_client.list_spans(PROJECT_ID, ex_id)
                orig_rels = admin_client.list_relations(PROJECT_ID, ex_id)
                
                if not orig_spans: continue

                id_mapping = {}
                for span in orig_spans:
                    try:
                        new_span = user_client.create_span(
                            project_id=PROJECT_ID,
                            example_id=ex_id,
                            start_offset=span.start_offset,
                            end_offset=span.end_offset,
                            label=span.label
                        )
                        id_mapping[span.id] = new_span.id
                    except: pass

                if not orig_rels:
                    continue
                
                for rel in orig_rels:
                    try:
                        n_f = id_mapping.get(rel.from_id)
                        n_t = id_mapping.get(rel.to_id)
                        if n_f and n_t:
                            user_client.create_relation(
                                project_id=PROJECT_ID,
                                example_id=ex_id,
                                from_id=n_f,
                                to_id=n_t,
                                label=rel.type
                            )
                        else:
                            logger.warning(
                                f"No se pudo mapear relación en doc {ex_id}: "
                                f"Origen({rel.from_id}->{n_f}), Destino({rel.to_id}->{n_t})"
                            )
                    except Exception as e:
                        logger.error(f"Error al crear relación en doc {ex_id}: {e}")
            logger.info(f"✓ {user.username} listo.")
        except Exception as e:
            logger.error(f"Error en usuario {user.username}: {e}")

if __name__ == "__main__":
    replicate_everything()