from __future__ import annotations

from datetime import datetime, timedelta, timezone

from medikristal.config import load_settings
from medikristal.db import SessionLocal, ConfigurationState
from medikristal.provider_budget import reserve_provider_budget
from medikristal.security import AuthContext
from medikristal.store import create_entity, get_configuration
from medikristal.errors import DomainError


def _ts(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat().replace('+00:00','Z')


def test_at017_budget_reservation_is_bounded():
    ctx=AuthContext('00000000-0000-4000-8000-000000000001','p',frozenset({'*'}))
    with SessionLocal() as db:
        cfg,_=get_configuration(db,ctx,load_settings().configuration_default)
        cfg.update({'mode':'online_extended','network_scope':'internet','paid_budget_minor':100,'execution_policy':'proposal_only','provider_allowlist':['paid']})
        state=db.get(ConfigurationState,ctx.tenant_id); state.data=cfg
        create_entity(db,ctx,'ProviderPolicy',{'provider_id':'paid','enabled':True,'allowed_modes':['online_extended'],'allows_patient_data':False,'allowed_purposes':['terminology_lookup'],'budget_minor':100,'currency':'CAD','period_start':_ts(-1),'period_end':_ts(1),'fallback_capability':None},foreign_key='paid')
        db.commit()
    with SessionLocal() as db:
        reserve_provider_budget(db,ctx,'paid',80,load_settings().configuration_default); db.commit()
    with SessionLocal() as db:
        try:
            reserve_provider_budget(db,ctx,'paid',30,load_settings().configuration_default)
        except DomainError as e:
            assert e.code=='budget_exceeded'
        else:
            raise AssertionError('budget should have been exceeded')
