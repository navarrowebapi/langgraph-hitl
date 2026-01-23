"""
Parser inteligente para arquivos de regras

Extrai regras de arquivos .txt estruturados, identificando:
- Seções (SEÇÃO, CLÁUSULA)
- IDs de regras (REGRA XXX-XXX, CLÁUSULA X.X)
- Metadados automáticos (domain, tipo_regra, departamento)
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime


class RuleParser:
    """Parser inteligente para arquivos de regras estruturados"""
    
    # Padrões para identificar regras
    # Aceita IDs como: TEST-001, COB-TEST-001, AUD-TEST-001, ou 1.1 (cláusulas)
    REGRA_PATTERN = re.compile(r'^(REGRA|CLÁUSULA)\s+([A-Z]+(?:-[A-Z]+)*-\d+|[\d.]+):\s*(.+)$', re.MULTILINE)
    SECAO_PATTERN = re.compile(r'^SEÇÃO\s+\d+:\s*(.+)$|^CLÁUSULA\s+\d+:\s*(.+)$', re.MULTILINE)
    
    # Mapeamento de palavras-chave para domínios
    DOMAIN_KEYWORDS = {
        'faturamento': ['faturamento', 'fatura', 'pagamento', 'valor', 'aprovação', 'auditoria'],
        'planos_e_cobertura': ['cobertura', 'plano', 'procedimento', 'código', 'autorização'],
        'juridico': ['contrato', 'cláusula', 'termo', 'condição', 'legal'],
        'cadastro': ['cadastro', 'dados', 'beneficiário', 'atualização'],
        'atendimento': ['atendimento', 'reclamação', 'solicitação', 'suporte']
    }
    
    # Mapeamento de palavras-chave para tipo de regra
    TIPO_REGRA_KEYWORDS = {
        'faturamento': ['aprovação', 'faturamento', 'valor'],
        'auditoria': ['auditoria', 'revisão', 'análise'],
        'cobertura': ['cobertura', 'procedimento', 'código'],
        'autorização': ['autorização', 'prévia', 'aprovação']
    }
    
    @staticmethod
    def infer_domain(text: str, section: str = "") -> str:
        """
        Infere o domínio baseado no conteúdo do texto e seção
        
        Args:
            text: Texto da regra
            section: Nome da seção
            
        Returns:
            Domínio inferido (faturamento, planos_e_cobertura, juridico, etc)
        """
        text_lower = (text + " " + section).lower()
        
        # Contar ocorrências de palavras-chave por domínio
        domain_scores = {}
        for domain, keywords in RuleParser.DOMAIN_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        
        return "outros"
    
    @staticmethod
    def infer_tipo_regra(text: str, section: str = "") -> str:
        """
        Infere o tipo de regra baseado no conteúdo
        
        Args:
            text: Texto da regra
            section: Nome da seção
            
        Returns:
            Tipo de regra inferido
        """
        text_lower = (text + " " + section).lower()
        
        for tipo, keywords in RuleParser.TIPO_REGRA_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                return tipo
        
        return "outros"
    
    @staticmethod
    def infer_departamento(domain: str, section: str = "") -> str:
        """
        Infere o departamento baseado no domínio e seção
        
        Args:
            domain: Domínio da regra
            section: Nome da seção
            
        Returns:
            Nome do departamento
        """
        mapping = {
            'faturamento': 'Faturamento',
            'planos_e_cobertura': 'Cobertura',
            'juridico': 'Jurídico',
            'cadastro': 'Cadastro',
            'atendimento': 'Atendimento'
        }
        
        dept = mapping.get(domain, 'Outros')
        
        # Ajustar baseado na seção
        section_lower = section.lower()
        if 'auditoria' in section_lower:
            return 'Auditoria'
        if 'cobertura' in section_lower:
            return 'Cobertura'
        
        return dept
    
    @classmethod
    def parse_file(cls, file_path: str) -> List[Dict]:
        """
        Parse um arquivo de regras e extrai todas as regras com metadados
        
        Args:
            file_path: Caminho para o arquivo .txt
            
        Returns:
            Lista de dicionários com regras e metadados completos
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(file_path)
        rules = []
        current_section = ""
        line_number = 0
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Detectar seção
            secao_match = cls.SECAO_PATTERN.match(line)
            if secao_match:
                current_section = secao_match.group(1) or secao_match.group(2) or ""
                continue
            
            # Detectar regra
            regra_match = cls.REGRA_PATTERN.match(line)
            if regra_match:
                tipo = regra_match.group(1)  # REGRA ou CLÁUSULA
                rule_id = regra_match.group(2)  # FAT-001 ou 1.1
                rule_text = regra_match.group(3)
                
                # Formatar rule_id completo
                if tipo == "CLÁUSULA":
                    full_rule_id = f"CLÁUSULA-{rule_id}"
                else:
                    full_rule_id = f"REGRA-{rule_id}"
                
                # Inferir metadados
                domain = cls.infer_domain(rule_text, current_section)
                tipo_regra = cls.infer_tipo_regra(rule_text, current_section)
                departamento = cls.infer_departamento(domain, current_section)
                
                # Criar metadados completos
                metadata = {
                    "source": filename,
                    "section": current_section or "Geral",
                    "rule_id": full_rule_id,
                    "page": "1",  # Pode ser melhorado com parser de PDF
                    "line_range": f"{i}-{i}",
                    "tipo_regra": tipo_regra,
                    "domain": domain,
                    "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "valid_from": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "departamento": departamento
                }
                
                rules.append({
                    "text": rule_text,
                    "metadata": metadata
                })
        
        return rules
    
    @classmethod
    def parse_folder(cls, folder_path: str) -> List[Dict]:
        """
        Parse todos os arquivos .txt de uma pasta
        
        Args:
            folder_path: Caminho para a pasta
            
        Returns:
            Lista de todas as regras encontradas em todos os arquivos
        """
        all_rules = []
        folder = Path(folder_path)
        
        for txt_file in folder.glob("*.txt"):
            try:
                rules = cls.parse_file(str(txt_file))
                all_rules.extend(rules)
                print(f"✅ Parseado {txt_file.name}: {len(rules)} regras encontradas")
            except Exception as e:
                print(f"❌ Erro ao parsear {txt_file.name}: {e}")
        
        return all_rules
