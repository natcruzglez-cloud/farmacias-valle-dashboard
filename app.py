from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title='Farmacias Valle | Dashboard', page_icon='📊', layout='wide')
BASE=Path(__file__).parent
BLUE='#176B9B'; ORANGE='#C46A13'; TEAL='#147D73'
MONTHS=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
st.markdown('''<style>
.stApp {background:#F7F9FC;color:#172B40}
h1,h2,h3 {letter-spacing:-.035em}
[data-testid="stMetric"] {background:white;border:1px solid #DBE3ED;border-radius:14px;padding:16px;min-height:135px}
[data-testid="stMetricValue"] {font-size:1.8rem}
[data-testid="stSidebar"] {background:#EDF2F7}
</style>''',unsafe_allow_html=True)

@st.cache_data
def load_data():
    d=pd.read_csv(BASE/'ventas.csv',parse_dates=['Mes'])
    i=pd.read_csv(BASE/'inpc.csv',parse_dates=['Mes'])
    assert len(d)==1200 and not d.duplicated(['Mes','Producto_ID']).any()
    d=d.merge(i,on='Mes',how='left',validate='many_to_one')
    assert d.INPC.notna().all()
    d['Ingreso_Real']=d.Ingreso_Mensual*137.949/d.INPC
    d['Anio']=d.Mes.dt.year;d['Mes_Num']=d.Mes.dt.month
    return d

def growth(a,b): return (a/b-1)*100 if b else None

def metrics(d):
    u=d.Unidades_Vendidas.sum();r=d.Ingreso_Mensual.sum()
    return [r,u,r/u if u else 0,d.Ingreso_Real.sum()]

def fmt(v,digits=0): return f'{v:,.{digits}f}'

def style(fig,height=340):
    fig.update_layout(height=height,margin=dict(l=10,r=10,t=20,b=10),paper_bgcolor='white',plot_bgcolor='white',font=dict(family='Arial',size=13,color='#172B40'),legend_title_text='',legend=dict(orientation='h',y=1.13,x=0),hoverlabel=dict(bgcolor='white'))
    fig.update_xaxes(showgrid=False);fig.update_yaxes(gridcolor='#E7EDF3',zeroline=False)
    return fig

df=load_data()
with st.sidebar:
    st.title('Farmacias Valle')
    st.caption('TABLERO DE DESEMPEÑO COMERCIAL')
    year=st.selectbox('Año de análisis',list(range(2020,2025)),index=4)
    start,end=st.select_slider('Meses del periodo',options=list(range(1,13)),value=(1,12),format_func=lambda x: MONTHS[x-1])
    categories=st.multiselect('Categorías',sorted(df.Categoria.unique()),default=sorted(df.Categoria.unique()))
    options=sorted(df.loc[df.Categoria.isin(categories),'Producto_Nombre'].unique())
    products=st.multiselect('Productos (vacío = todos)',options)
    st.caption('Comparación: los mismos meses, categorías y productos del año anterior.')
    st.divider()
    st.caption('Caso académico · UNRC\n\nCiencia de Datos para Negocios\n\nSéptimo semestre · Natalia Cruz')
mask=df.Categoria.isin(categories)&df.Mes_Num.between(start,end)
if products: mask &=df.Producto_Nombre.isin(products)
cur=df[mask & df.Anio.eq(year)].copy(); prev=df[mask & df.Anio.eq(year-1)].copy()
if cur.empty:
    st.info('Selecciona al menos una categoría para mostrar el análisis.');st.stop()
a=metrics(cur);b=metrics(prev);delta=[growth(x,y) for x,y in zip(a,b)]
st.caption(f'ANÁLISIS COMERCIAL / {year} · {MONTHS[start-1]}–{MONTHS[end-1]} · {cur.Producto_ID.nunique()} productos')
if delta[0] is not None:
    verb='crecen' if delta[0]>=0 else 'caen'
    st.title(f'Los ingresos {verb} {abs(delta[0]):.1f}%; el cambio real es {delta[3]:+.1f}%')
else: st.title('Ventas e inventario para orientar las compras')
st.markdown('**Decisión:** priorizar la revisión de compras por producto y temporada. **Audiencia:** gerencia comercial y responsable de compras.')
labels=['Ingresos nominales','Unidades vendidas','Ingreso por unidad','Ingresos a precios dic. 2024']
for col,label,value,change,k in zip(st.columns(4),labels,a,delta,range(4)):
    col.metric(label,fmt(value,2 if k==2 else 0),None if change is None else f'{change:+.2f}% interanual',delta_color='off' if k==2 else 'normal')
st.caption('Importes en unidades monetarias del anexo (moneda no especificada). “Real” = ajuste con INPC general; no representa utilidad. Sin metas documentadas, el contexto es interanual.')
if prev.empty: st.warning('2020 no tiene un año anterior disponible. Se muestran valores, sin calcular variaciones interanuales.')
else:
    st.info(f'Lectura del periodo: el volumen cambia {delta[1]:+.2f}% y el ingreso promedio por unidad {delta[2]:+.2f}%. Este último combina precios y mezcla de productos; no identifica por sí solo un efecto causal.')

main,method=st.tabs(['Explorar resultados','Método y fuentes'])
with main:
    left,right=st.columns(2)
    with left:
        st.subheader('01 · La trayectoria de los ingresos')
        monthly=cur.groupby('Mes_Num')[['Ingreso_Mensual','Ingreso_Real']].sum().reset_index()
        fig=go.Figure()
        for field,label,color,dash in [('Ingreso_Mensual','Nominal',BLUE,'solid'),('Ingreso_Real','A precios dic. 2024',ORANGE,'dash')]:
            fig.add_trace(go.Scatter(x=monthly.Mes_Num,y=monthly[field],mode='lines+markers',name=label,line=dict(color=color,dash=dash,width=3),hovertemplate='%{y:,.2f}<extra>'+label+'</extra>'))
        fig.update_xaxes(tickmode='array',tickvals=list(range(1,13)),ticktext=MONTHS,title='Mes');fig.update_yaxes(title='Unidades monetarias',rangemode='tozero')
        st.plotly_chart(style(fig),use_container_width=True)
        peak=monthly.loc[monthly.Ingreso_Mensual.idxmax()]
        st.caption(f'{MONTHS[int(peak.Mes_Num)-1]} registra el mayor ingreso nominal del periodo: {fmt(peak.Ingreso_Mensual,2)}. El ajuste se aplica mes a mes antes de sumar.')
    with right:
        st.subheader('02 · Qué categorías mueven el volumen')
        comp=pd.concat([cur,prev]).groupby(['Categoria','Anio'],as_index=False).Unidades_Vendidas.sum()
        comp['Periodo']=comp.Anio.astype(str)
        fig=px.bar(comp,x='Unidades_Vendidas',y='Categoria',color='Periodo',barmode='group',orientation='h',color_discrete_map={str(year):BLUE,str(year-1):ORANGE},labels={'Unidades_Vendidas':'Unidades vendidas','Categoria':''})
        fig.update_xaxes(rangemode='tozero')
        st.plotly_chart(style(fig),use_container_width=True)
        lead=cur.groupby('Categoria').Ingreso_Mensual.sum().sort_values(ascending=False)
        st.caption(f'{lead.index[0]} aporta {lead.iloc[0]/a[0]*100:.1f}% de los ingresos seleccionados. La comparación usa los mismos meses del año previo.')
    st.subheader('03 · Qué tan variables son las ventas por producto')
    fig=px.box(cur,x='Unidades_Vendidas',y='Producto_Nombre',orientation='h',points='all',color_discrete_sequence=[BLUE],labels={'Unidades_Vendidas':'Unidades vendidas por mes','Producto_Nombre':''},hover_data=['Mes','Temporada'])
    st.plotly_chart(style(fig,max(350,cur.Producto_ID.nunique()*27)),use_container_width=True)
    st.caption('Cada punto representa un producto–mes. La caja resume el 50% central, la línea es la mediana y los bigotes se extienden hasta 1.5 veces el rango intercuartílico. Con un solo mes la caja se reduce a un punto; amplía el periodo para estudiar dispersión.')
    st.subheader('04 · Stock reportado frente a ventas del último mes')
    latest=cur[cur.Mes.eq(cur.Mes.max())].copy()
    fig=px.scatter(latest,x='Unidades_Vendidas',y='Stock_Disponible',text='Producto_ID',hover_name='Producto_Nombre',color_discrete_sequence=[TEAL],labels={'Unidades_Vendidas':'Unidades vendidas en el mes','Stock_Disponible':'Stock reportado (unidades)'})
    fig.update_traces(marker=dict(size=11),textposition='top center')
    lim=max(latest.Unidades_Vendidas.max(),latest.Stock_Disponible.max())*1.1
    fig.add_trace(go.Scatter(x=[0,lim],y=[0,lim],mode='lines',name='Referencia 1:1',line=dict(color='#788694',dash='dash'),hoverinfo='skip'))
    fig.update_xaxes(rangemode='tozero');fig.update_yaxes(rangemode='tozero')
    st.plotly_chart(style(fig,390),use_container_width=True)
    st.caption(f'Corte: {cur.Mes.max():%Y-%m}. El stock no se suma entre meses. La diagonal solo compara magnitudes; no es una meta ni demuestra desabasto. El anexo no define cuándo se mide la existencia.')
    with st.expander('Ver y descargar los datos seleccionados'):
        st.dataframe(cur.drop(columns=['Anio','Mes_Num']),use_container_width=True,hide_index=True)
        st.download_button('Descargar selección CSV',cur.to_csv(index=False).encode('utf-8-sig'),'farmacias_seleccion.csv','text/csv')
with method:
    st.subheader('Dos fuentes unidas por mes')
    st.markdown('''**Fuente 1.** Anexo del profesor: *Farmacias_Valle_Demanda_1200(1).pdf*. 1,200 registros, 20 productos y 60 meses (2020–2024). No se declara si los datos son reales o simulados; se usan como caso académico.

**Fuente 2.** INPC nacional mensual, elaborado por INEGI y consultado en la [Secretaría de Finanzas de Chiapas](https://www.ingresos.finanzaschiapas.gob.mx/services/asist-fiscal/inpc.asp), cotejado con [Finanzas Oaxaca](https://www.finanzasoaxaca.gob.mx/indicadores-fiscales-2/). [Metodología y base del INEGI](https://www.inegi.org.mx/programas/inpc/). Consulta: 10 de octubre de 2026. Base del índice: segunda quincena de julio de 2018 = 100.

**Integración.** Unión muchos-a-uno por mes con 60 valores de INPC. Se valida que los 1,200 registros se conserven y todos tengan índice. Se extraen las columnas partidas en pares de páginas del PDF, respetando el orden de sus filas.

**Controles.** Sin duplicados producto–mes ni valores faltantes en los campos extraídos. Cada producto tiene 60 meses. En todos los registros, ingreso = unidades × precio, con tolerancia de un centavo. Las categorías del anexo se conservan; deben revisarse antes de un uso operativo, pues son etiquetas de origen y no una clasificación clínica validada.

**Justificación visual.** Líneas para evolución; barras agrupadas para comparar categorías; cajas y puntos para distribución; dispersión para relacionar stock y ventas en un corte. Las tarjetas resumen KPIs, siempre con un periodo comparable. Colores azul y naranja, marcadores, etiquetas y estilos de línea evitan depender únicamente del color.''')
    st.markdown('''| Indicador | Fórmula | Contexto |
|---|---|---|
| Ingresos nominales | Suma de Ingreso_Mensual | Mismos meses del año previo |
| Unidades vendidas | Suma de Unidades_Vendidas | Mismos meses del año previo |
| Ingreso por unidad | Suma de ingresos / suma de unidades | No es promedio simple ni ticket por cliente |
| Ingresos reales | Suma de ingreso mensual × 137.949 / INPC mensual | Valor a precios de diciembre de 2024 |

Variación interanual = (valor actual / valor previo − 1) × 100. Los filtros de categoría y producto se aplican a ambos periodos. El INPC nunca se suma como si fuera una venta.''')
    st.warning('Límites: no hay costos, márgenes, clientes, sucursales, compras, caducidades ni tiempos de entrega. Ventas no equivale a demanda total; las promociones no identifican causalidad. El INPC general aproxima poder adquisitivo y no la inflación específica de medicamentos. La moneda no está declarada.')
    st.markdown('**Decisión recomendada:** revisar mensualmente las compras según unidades vendidas por producto y su variación; antes de definir pedidos, incorporar inventario inicial y final, tiempos de reposición y caducidades. No incrementar compras automáticamente al ritmo de los ingresos nominales.')
    st.caption('Aplicación escrita en Streamlit. La versión web utiliza Stlite para ejecutar Python en el navegador. El notebook documenta y reproduce los cálculos.')
