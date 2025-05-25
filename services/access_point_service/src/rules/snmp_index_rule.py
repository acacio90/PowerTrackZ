from typing import List, Dict, Any
import json

class SNMPIndexRule:
    def __init__(self):
        self.name = "snmp_index_rule"
        self.description = "Extrai o SNMPINDEX como ID da tabela de pontos de acesso"

    def process(self, data: str) -> List[Dict[str, Any]]:
        """
        Processa os dados JSON e extrai o SNMPINDEX como ID
        
        Args:
            data (str): String JSON contendo os dados dos pontos de acesso
            
        Returns:
            List[Dict[str, Any]]: Lista de dicionários com os dados processados
        """
        try:
            # Converte a string JSON para uma lista de dicionários
            ap_data = json.loads(data)
            
            # Processa cada item para extrair o SNMPINDEX como ID
            processed_data = []
            for item in ap_data:
                processed_item = {
                    "id": item["{#SNMPINDEX}"],
                    "name": item["{#RADIOAPNAME}"]
                }
                processed_data.append(processed_item)
                
            return processed_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao decodificar JSON: {str(e)}")
        except KeyError as e:
            raise ValueError(f"Campo obrigatório não encontrado: {str(e)}")
        except Exception as e:
            raise Exception(f"Erro ao processar dados: {str(e)}")

    def validate(self, data: str) -> bool:
        """
        Valida se os dados estão no formato esperado
        
        Args:
            data (str): String JSON para validar
            
        Returns:
            bool: True se os dados são válidos, False caso contrário
        """
        try:
            ap_data = json.loads(data)
            if not isinstance(ap_data, list):
                return False
                
            for item in ap_data:
                if not isinstance(item, dict):
                    return False
                if "{#SNMPINDEX}" not in item or "{#RADIOAPNAME}" not in item:
                    return False
                    
            return True
            
        except:
            return False 