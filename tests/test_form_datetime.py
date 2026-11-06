import pytest
import pymupdf as f
from backend.form_actions import value
from backend.forms import form_model
from backend.engine import DocumentError
from backend.form_data import flatten_form
from tests.test_form_standard_actions import source,fill

CASES=[('dd/mm/yyyy','29/02/2024'),('mm/dd/yyyy','02/29/2024'),('yyyy-mm-dd','2024-02-29'),('dd.mm.yyyy','29.02.2024')]


@pytest.mark.parametrize('date,day',CASES)
@pytest.mark.parametrize('clock,text',[('HH:MM','23:59'),('HH:MM:ss','00:01:59')])
def test_fill_save_reopen_and_flatten_combined_date_time_keeps_actions_and_appearance(date,day,clock,text):
    pattern=date+' '+clock;initial=source(f'AFDate_FormatEx("{pattern}");',f'AFDate_KeystrokeEx("{pattern}");',initial='');entered=day+' '+text;out=fill(initial,entered)
    with f.open(stream=initial) as a,f.open(stream=out) as b:
        row=form_model(b)['fields'][0];w=next(b[0].widgets());old=next(a[0].widgets())
        assert row['editable'] and row['value']==entered and row['display_value']==entered
        assert w.field_value==entered and entered in b[0].get_text()
        assert a.xref_get_key(old.xref,'AA')==b.xref_get_key(w.xref,'AA')
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
    again=fill(out,entered);flat=flatten_form(again,[])
    with f.open(stream=again) as a,f.open(stream=flat) as b:assert not list(b[0].widgets() or []) and a[0].get_pixmap().samples==b[0].get_pixmap().samples


@pytest.mark.parametrize('text',['29/02/2023 12:00','31/04/2026 12:00','06/11/2026 24:00','06/11/2026 10:60','6/11/2026 10:00','06/11/2026 1:00','06/11/2026 10:00Z','06/11/2026 10:00 extra'])
def test_invalid_date_or_time_is_rejected_atomically(text):
    base=source('AFDate_FormatEx("dd/mm/yyyy HH:MM");','AFDate_KeystrokeEx("dd/mm/yyyy HH:MM");',initial='')
    with pytest.raises(DocumentError,match='fecha no es válida'):fill(base,text)


def test_mismatched_combined_date_key_action_remains_read_only():
    base=source('AFDate_FormatEx("dd/mm/yyyy HH:MM");','AFDate_KeystrokeEx("dd/mm/yyyy HH:MM:ss");',initial='')
    with f.open(stream=base) as d:assert not form_model(d)['fields'][0]['editable']
