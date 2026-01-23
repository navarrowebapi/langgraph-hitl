"""
Scheduler para execução automática de ingestão

Executa ingestão diária às 6:00 (configurável via INGESTION_SCHEDULE_TIME)
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Adicionar src ao path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from services.ingestion.service import IngestionService


def run_ingestion():
    """Executa a ingestão de documentos"""
    print(f"\n{'='*60}")
    print(f"⏰ Execução automática de ingestão - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    try:
        service = IngestionService()
        result = service.ingest_all()
        
        if result["success"]:
            print(f"✅ Ingestão automática concluída com sucesso!")
            print(f"   Regras indexadas: {result['rules_indexed']}")
        else:
            print(f"⚠️  Ingestão automática falhou: {result.get('error', 'Erro desconhecido')}")
            
    except Exception as e:
        print(f"❌ Erro na ingestão automática: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Inicia o scheduler"""
    # Obter horário configurado (padrão: 6:00)
    schedule_time = os.getenv("INGESTION_SCHEDULE_TIME", "06:00")
    hour, minute = map(int, schedule_time.split(":"))
    
    print(f"🚀 Iniciando scheduler de ingestão")
    print(f"   Horário configurado: {schedule_time}")
    print(f"   Pressione Ctrl+C para parar")
    
    scheduler = BlockingScheduler()
    
    # Agendar execução diária
    scheduler.add_job(
        run_ingestion,
        trigger=CronTrigger(hour=hour, minute=minute),
        id='daily_ingestion',
        name='Ingestão diária de documentos',
        replace_existing=True
    )
    
    # Executar imediatamente na primeira vez (opcional)
    # Descomente a linha abaixo se quiser executar na inicialização
    # run_ingestion()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n⏹️  Scheduler interrompido")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
