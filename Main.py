#!/usr/bin/env python3
import sys, sqlite3
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import QDate, QTime
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDateEdit, QTimeEdit, QGroupBox, QGridLayout, QMessageBox, QSplitter, QFrame, QStatusBar
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates

DATE_FORMAT = '%d/%m/%Y %H:%M:%S'

class PlotCanvas(FigureCanvas):
    def __init__(self,parent=None,w=7,h=5,dpi=100):
        fig=Figure(figsize=(w,h),dpi=dpi)
        self.ax=fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        fig.tight_layout()
    def clear(self):
        self.figure.clf()
        self.ax=self.figure.add_subplot(111)
        self.draw()

class LeituraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Leitura Viewer')
        self.resize(900,600)
        self.db_path=None
        self.all_rows=[]
        self.dt_start=None
        self.dt_end=None
        self._build_ui()

    def _build_ui(self):
        central=QWidget(); self.setCentralWidget(central)
        main_layout=QHBoxLayout(); central.setLayout(main_layout)

        # Controles
        ctrl_box=QGroupBox('Controles'); ctrl_layout=QVBoxLayout(); ctrl_box.setLayout(ctrl_layout)
        btn_open=QPushButton('Abrir .db'); btn_open.clicked.connect(self.open_db); ctrl_layout.addWidget(btn_open)

        # Filtro
        filt_box=QGroupBox('Filtro Data/Hora'); gf=QGridLayout(); filt_box.setLayout(gf)
        today=QDate.currentDate()
        self.start_date=QDateEdit(today); self.start_date.setCalendarPopup(True)
        self.end_date=QDateEdit(today); self.end_date.setCalendarPopup(True)
        self.start_time=QTimeEdit(QTime(12,0)); self.start_time.setDisplayFormat('HH:mm')
        self.end_time=QTimeEdit(QTime(20,0)); self.end_time.setDisplayFormat('HH:mm')
        gf.addWidget(QLabel('Início:'),0,0); gf.addWidget(self.start_date,0,1); gf.addWidget(self.start_time,0,2)
        gf.addWidget(QLabel('Fim:'),1,0); gf.addWidget(self.end_date,1,1); gf.addWidget(self.end_time,1,2)
        btn_apply=QPushButton('Aplicar filtro'); btn_apply.clicked.connect(self.apply_filter)
        ctrl_layout.addWidget(filt_box); ctrl_layout.addWidget(btn_apply)

        # Botões de gráficos
        grp_graph=QGroupBox('Gráficos'); vgb=QVBoxLayout(); grp_graph.setLayout(vgb)
        self.btn_temp_time=QPushButton('Temperatura x Tempo'); self.btn_temp_time.clicked.connect(self.plot_temp_time); vgb.addWidget(self.btn_temp_time)
        self.btn_hum_time=QPushButton('Umidade x Tempo'); self.btn_hum_time.clicked.connect(self.plot_hum_time); vgb.addWidget(self.btn_hum_time)
        self.btn_cpu_time=QPushButton('Temp_CPU x Tempo'); self.btn_cpu_time.clicked.connect(self.plot_cpu_time); vgb.addWidget(self.btn_cpu_time)
        self.btn_all_time=QPushButton('Comparativo'); self.btn_all_time.clicked.connect(self.plot_all_time); vgb.addWidget(self.btn_all_time)
        self.btn_t_u=QPushButton('Temp x Umid'); self.btn_t_u.clicked.connect(self.plot_temp_vs_umid); vgb.addWidget(self.btn_t_u)
        self.btn_t_c=QPushButton('Temp x CPU'); self.btn_t_c.clicked.connect(self.plot_temp_vs_cpu); vgb.addWidget(self.btn_t_c)
        self.btn_u_c=QPushButton('Umid x CPU'); self.btn_u_c.clicked.connect(self.plot_umid_vs_cpu); vgb.addWidget(self.btn_u_c)
        self.btn_matrix=QPushButton('Matriz'); self.btn_matrix.clicked.connect(self.plot_matrix); vgb.addWidget(self.btn_matrix)
        ctrl_layout.addWidget(grp_graph); ctrl_layout.addStretch()

        # Canvas
        plot_frame=QFrame(); plot_layout=QVBoxLayout(); plot_frame.setLayout(plot_layout)
        self.canvas=PlotCanvas(self,8,6); plot_layout.addWidget(self.canvas)
        self.status=QStatusBar(); self.setStatusBar(self.status)
        splitter=QSplitter(); splitter.addWidget(ctrl_box); splitter.addWidget(plot_frame); splitter.setSizes([250,650])
        main_layout.addWidget(splitter)

    # Carregar banco
    def open_db(self):
        path,_=QFileDialog.getOpenFileName(self,'Abrir .db',str(Path.home()),'SQLite DB Files (*.db *.sqlite);;All Files (*)')
        if not path: return
        self.db_path=path; self.all_rows=[]
        conn=sqlite3.connect(self.db_path); cur=conn.cursor()
        try:
            # Ordenar por datahora
            cur.execute('SELECT id,datahora,temperatura,umidade,temp_cpu FROM leitura ORDER BY datahora')
            for r in cur.fetchall():
                _id,dt_txt,temp,umid,temp_cpu=r
                dt=None
                for fmt in ('%d/%m/%Y %H:%M:%S','%d/%m/%Y %H:%M'):
                    try:
                        dt=datetime.strptime(dt_txt.strip(),fmt)
                        if fmt=='%d/%m/%Y %H:%M':
                            dt=dt.replace(second=0)
                        break
                    except:
                        continue
                if dt:
                    self.all_rows.append({'id':_id,'datahora':dt,'temperatura':temp,'umidade':umid,'temp_cpu':temp_cpu})
        except Exception as e:
            QMessageBox.critical(self,'Erro',f'Erro ao consultar tabela: {e}')
        conn.close()
        self.status.showMessage(f'{len(self.all_rows)} registros carregados')

    # Aplicar filtro
    def apply_filter(self):
        sd=self.start_date.date(); ed=self.end_date.date()
        st=self.start_time.time(); et=self.end_time.time()
        self.dt_start=datetime(sd.year(),sd.month(),sd.day(),st.hour(),st.minute(),0)
        self.dt_end=datetime(ed.year(),ed.month(),ed.day(),et.hour(),et.minute(),59)
        if self.dt_end<self.dt_start:
            QMessageBox.critical(self,'Erro','Fim antes do início')
            return
        self.status.showMessage('Filtro aplicado')

    # Filtrar dados
    def _get_filtered(self):
        if not self.all_rows or not self.dt_start: return []
        return [r for r in self.all_rows if self.dt_start<=r['datahora']<=self.dt_end]

    # Função comum de gráfico temporal
    def _plot_time_series(self,xs,ys,ylabel,title):
        self.canvas.clear(); ax=self.canvas.ax
        ax.plot(xs,ys,'-o',markersize=3)
        ax.set_title(title); ax.set_ylabel(ylabel); ax.set_xlabel('Data Hora')
        ax.set_xlim(self.dt_start,self.dt_end)  # força eixo X igual ao filtro
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        for l in ax.get_xticklabels(): l.set_rotation(30); l.set_horizontalalignment('right')
        ax.grid(True); self.canvas.draw()

    # Gráficos
    def plot_temp_time(self):
        rows=self._get_filtered(); 
        if not rows: QMessageBox.information(self,'Sem dados','Nenhum registro'); return
        self._plot_time_series([r['datahora'] for r in rows],[r['temperatura'] for r in rows],'Temperatura','Temperatura x Tempo')

    def plot_hum_time(self):
        rows=self._get_filtered()
        if not rows: QMessageBox.information(self,'Sem dados','Nenhum registro'); return
        self._plot_time_series([r['datahora'] for r in rows],[r['umidade'] for r in rows],'Umidade','Umidade x Tempo')

    def plot_cpu_time(self):
        rows=self._get_filtered()
        if not rows: QMessageBox.information(self,'Sem dados','Nenhum registro'); return
        self._plot_time_series([r['datahora'] for r in rows],[r['temp_cpu'] for r in rows],'Temp_CPU','Temp_CPU x Tempo')

    def plot_all_time(self):
        rows=self._get_filtered()
        if not rows: QMessageBox.information(self,'Sem dados','Nenhum registro'); return
        xs=[r['datahora'] for r in rows]; t=[r['temperatura'] for r in rows]; u=[r['umidade'] for r in rows]; c=[r['temp_cpu'] for r in rows]
        self.canvas.clear(); ax=self.canvas.ax
        ax.plot(xs,t,'-o',label='Temp',markersize=3); ax.plot(xs,u,'-o',label='Umid',markersize=3); ax.plot(xs,c,'-o',label='CPU',markersize=3)
        ax.set_title('Comparativo'); ax.set_xlabel('Data Hora'); ax.set_xlim(self.dt_start,self.dt_end)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M')); ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        for l in ax.get_xticklabels(): l.set_rotation(30); l.set_horizontalalignment('right'); ax.legend(); ax.grid(True); self.canvas.draw()

    def plot_temp_vs_umid(self):
        rows=self._get_filtered(); 
        if not rows: QMessageBox.information(self,'Sem dados','Nenhum registro'); return
        self.canvas.clear(); ax=self.canvas.ax
        ax.scatter([r['temperatura'] for r in rows],[r['umidade'] for r in rows])
        ax.set_xlabel('Temp'); ax.set_ylabel('Umid'); ax.set_title('Temp x Umid'); ax.grid(True); self.canvas.draw()

    def plot_temp_vs_cpu(self):
        rows=self._get_filtered(); 
        if not rows: QMessageBox.information(self,'Sem dados','Nenhum registro'); return
        self.canvas.clear(); ax=self.canvas.ax
        ax.scatter([r['temperatura'] for r in rows],[r['temp_cpu'] for r in rows])
        ax.set_xlabel('Temp'); ax.set_ylabel('CPU'); ax.set_title('Temp x CPU'); ax.grid(True); self.canvas.draw()

    def plot_umid_vs_cpu(self):
        rows=self._get_filtered(); 
        if not rows: QMessageBox.information(self,'Sem dados','Nenhum registro'); return
        self.canvas.clear(); ax=self.canvas.ax
        ax.scatter([r['umidade'] for r in rows],[r['temp_cpu'] for r in rows])
        ax.set_xlabel('Umid'); ax.set_ylabel('CPU'); ax.set_title('Umid x CPU'); ax.grid(True); self.canvas.draw()

    def plot_matrix(self):
        rows=self._get_filtered(); 
        if not rows: QMessageBox.information(self,'Sem dados','Nenhum registro'); return
        t=[r['temperatura'] for r in rows]; u=[r['umidade'] for r in rows]; c=[r['temp_cpu'] for r in rows]
        self.canvas.figure.clf(); ax1=self.canvas.figure.add_subplot(131); ax2=self.canvas.figure.add_subplot(132); ax3=self.canvas.figure.add_subplot(133)
        ax1.scatter(t,u); ax1.set_xlabel('Temp'); ax1.set_ylabel('Umid'); ax1.set_title('Temp x Umid'); ax1.grid(True)
        ax2.scatter(t,c); ax2.set_xlabel('Temp'); ax2.set_ylabel('CPU'); ax2.set_title('Temp x CPU'); ax2.grid(True)
        ax3.scatter(u,c); ax3.set_xlabel('Umid'); ax3.set_ylabel('CPU'); ax3.set_title('Umid x CPU'); ax3.grid(True)
        self.canvas.figure.tight_layout(); self.canvas.draw()

def main():
    app=QApplication(sys.argv)
    win=LeituraApp(); win.show()
    sys.exit(app.exec_())

if __name__=='__main__':
    main()
