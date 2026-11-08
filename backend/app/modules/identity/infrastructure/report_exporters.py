"""Serializadores binarios de RF-16. Nunca calculan ni publican calificaciones."""
from datetime import UTC, datetime
from io import BytesIO
from math import ceil
from importlib.resources import files
from threading import Lock
from xml.sax.saxutils import escape
from app.modules.identity.application.official_reports import ArchivoReporte

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
FONT_LOCK = Lock()


def metadatos(r):
    return [('Publicación oficial', str(r.id)), ('Versión de publicación', r.version),
        ('SHA-256 de publicación', r.sha256), ('Sesión', str(r.sesion_id)), ('Caso', r.caso),
        ('Versión histórica de caso', str(r.version_caso_id)),
        ('Publicada (UTC)', r.publicada_en.isoformat()), ('Generada (UTC)', r.generada_en.isoformat()),
        ('Grupo seleccionado', r.filtros.id_grupo),
        ('Estudiantes seleccionados', ', '.join(map(str,r.filtros.estudiantes)) or 'Todos'),
        ('Estado seleccionado', r.filtros.estado or 'Todos'), ('Orden', r.filtros.agrupar_por),
        ('Filas de resultados', len(r.filas)), ('Convocatorias retiradas', len(r.retiradas)),
        ('Antecedentes', 'Las retiradas no tienen nota. La publicación conserva sus identificadores, no sus nombres históricos.'),
        ('Duración', 'Tiempo real entre inicio y cierre del intento. Las ausencias no crean intentos ni duraciones.')]


RESULTADOS = ['Grupo ID','Grupo','Estudiante ID','Estudiante','Convocatoria','Participación',
    'Estado publicado','Nota oficial','Intentos','Resultado técnico seleccionado','Ausencia confirmada']
INTENTOS = ['Estudiante ID','Convocatoria','Participación','Intento','Número','Estado',
    'Inicio (UTC)','Cierre (UTC)','Duración real (segundos)','Duración concedida (segundos)']


def resultados(r):
    return [[f['grupo_id'],f['grupo_nombre'],f['id_estudiante'],f['nombre_estudiante'],f['convocatoria_id'],
        f['id_participacion'],f['situacion'],f['nota'],len(f['intentos']),f['id_resultado_intento'],
        f['id_ausencia']] for f in r.filas]


def intentos(r):
    return [[f['id_estudiante'],f['convocatoria_id'],f['id_participacion'],i['id_intento'],i['numero'],
        i['estado'],i['inicio'].astimezone(UTC).replace(tzinfo=None),
        i['fin'].astimezone(UTC).replace(tzinfo=None),i['segundos'],i['concedidos']]
        for f in r.filas for i in f['intentos']]


class ExportadorReportesOficiales:
    def exportar(self, fuente, formato):
        contenido = self._xlsx(fuente) if formato == 'xlsx' else self._pdf(fuente)
        return ArchivoReporte(contenido, XLSX if formato == 'xlsx' else 'application/pdf',
            f'resultados-{fuente.sesion_id}-v{fuente.version}.{formato}',
            fuente.id,fuente.version,fuente.sha256)

    def _xlsx(self, r):
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
        wb = Workbook();wb.remove(wb.active)
        tablas = [('Publicacion',['Dato','Valor'],metadatos(r)),
            ('Resultados',RESULTADOS,resultados(r)),('Intentos',INTENTOS,intentos(r)),
            ('Antecedentes',['Convocatoria','Estado','Nota'],[(c,'RETIRADA',None) for c in r.retiradas])]
        for nombre,cabeceras,filas in tablas:
            ws = wb.create_sheet(nombre);ws.append(cabeceras)
            for fila in filas:
                ws.append(fila)
            for row in ws:
                for c in row:
                    if isinstance(c.value,str):
                        # Una cadena académica jamás se interpreta como fórmula o enlace.
                        c.data_type = 's'
                        if c.value.lstrip().startswith(('=','+','-','@','\t','\r','\n')):
                            c.quotePrefix = True
                    if c.row == 1:
                        c.font=Font(bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor='23465C')
                    c.alignment=Alignment(vertical='top',wrap_text=True)
                    if isinstance(c.value, datetime):
                        c.number_format='yyyy-mm-dd hh:mm:ss'
                if row[0].row > 1:
                    ws.row_dimensions[row[0].row].height = 34 if nombre != 'Publicacion' else 46
            if nombre == 'Resultados':
                for row in ws.iter_rows(min_row=2):row[7].number_format='0.00'
            for col in range(1,len(cabeceras)+1):
                vals=[str(ws.cell(n,col).value or '') for n in range(1,ws.max_row+1)]
                ws.column_dimensions[get_column_letter(col)].width=min(56,max(16,max(map(len,vals))+2))
            for row in ws.iter_rows(min_row=2):
                lineas=max(max(1,sum(max(1,ceil(len(line)/max(1,ws.column_dimensions[c.column_letter].width-2)))
                    for line in str(c.value or '').split('\n'))) for c in row)
                ws.row_dimensions[row[0].row].height=max(24,14*lineas+8)
            ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions;ws.print_title_rows='1:1'
            ws.sheet_properties.pageSetUpPr.fitToPage=True
            ws.page_setup.orientation='landscape';ws.page_setup.paperSize=ws.PAPERSIZE_A4
            ws.page_setup.fitToWidth=1;ws.page_setup.fitToHeight=0
        out=BytesIO();wb.save(out);return out.getvalue()

    def _pdf(self,r):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,LongTable,TableStyle
        with FONT_LOCK:
            if 'SPSVera' not in pdfmetrics.getRegisteredFontNames():
                carpeta=files('reportlab').joinpath('fonts')
                pdfmetrics.registerFont(TTFont('SPSVera',str(carpeta.joinpath('Vera.ttf'))))
                pdfmetrics.registerFont(TTFont('SPSVeraBold',str(carpeta.joinpath('VeraBd.ttf'))))
        normal=ParagraphStyle('cuerpo',fontName='SPSVera',fontSize=8,leading=11,spaceAfter=5)
        titulo=ParagraphStyle('titulo',parent=normal,fontName='SPSVeraBold',fontSize=15,leading=19,spaceAfter=12)
        subtitulo=ParagraphStyle('subtitulo',parent=normal,fontName='SPSVeraBold',fontSize=10,leading=14,spaceBefore=10)
        cell=ParagraphStyle('celda',parent=normal,fontSize=7,leading=9,spaceAfter=0)
        out=BytesIO();doc=SimpleDocTemplate(out,pagesize=landscape(A4),rightMargin=30,leftMargin=30,
            topMargin=32,bottomMargin=34,title='Proyecto Nuclear - reporte académico oficial',author='Proyecto Nuclear')
        para=lambda x,style=normal:Paragraph(escape(str(x)) if x is not None else '',style)
        story=[para('Proyecto Nuclear',titulo),para('Reporte académico oficial',subtitulo)]
        story += [para(f'{k}: {v}') for k,v in metadatos(r) if v is not None]
        def tabla(headers,rows,widths):
            data=[[para(x,cell) for x in headers]]+[[para(x,cell) for x in row] for row in rows]
            t=LongTable(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCE6ED')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#9AA5AA')),
                ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
                ('BOTTOMPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6)]))
            story.append(t)
        story.append(para('Resultados publicados',subtitulo))
        if not r.filas:story.append(para('No hay resultados para los filtros seleccionados.'))
        else:
            tabla(['Grupo','Estudiante / ID','Convocatoria / Participación','Estado','Nota oficial','Intentos'],
                [[f['grupo_nombre'],f"{f['nombre_estudiante']} / {f['id_estudiante']}",
                  f"{f['convocatoria_id']} / {f['id_participacion'] if f['id_participacion'] is not None else 'Sin participación'}",
                  f['situacion'],format(f['nota'],'.2f'),len(f['intentos'])] for f in r.filas],
                  [110,175,235,85,80,90])
        if any(f['intentos'] for f in r.filas):
            story.append(para('Intentos históricos (sin recalcular notas)',subtitulo))
            tabla(['Estudiante / intento','Estado','Inicio UTC','Cierre UTC','Segundos reales','Concedidos'],
                [[f"{f['id_estudiante']} / {i['id_intento']} (n.º {i['numero']})",i['estado'],
                  i['inicio'].isoformat(),i['fin'].isoformat(),str(i['segundos']),str(i['concedidos'])]
                  for f in r.filas for i in f['intentos']], [100,85,190,190,105,105])
        story.append(para('Convocatorias retiradas: antecedentes excluidos de notas',subtitulo))
        if r.retiradas:tabla(['Convocatoria','Estado'],[(x,'RETIRADA') for x in r.retiradas],[540,235])
        else:story.append(para('Sin convocatorias retiradas en esta publicación.'))
        def pie(canvas,document):
            canvas.saveState();canvas.setFont('SPSVera',7)
            canvas.drawString(30,18,f'Publicación v{r.version} / {r.id}')
            canvas.drawRightString(810,18,f'Página {document.page}');canvas.restoreState()
        doc.build(story,onFirstPage=pie,onLaterPages=pie)
        return out.getvalue()
