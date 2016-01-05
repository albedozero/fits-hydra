#!/usr/bin/env python

VERSION_STR = 'v0.1'

import os
import shutil
import re
import wx
import wx.grid as grid
import pyfits

DEFAULT_TOKENS = ['OBJECT', 'FILTER', 'EXPTIME', 'DATE-OBS', 'FOCUSPOS', 'AIRMASS']

TOKENS_LIST = ['OBJECT', 'FILTER', 'EXPTIME', 'DATE-OBS', 'ORIGIN', 'TELESCOP', 'COMMENT', 'OBSERVER', 'PRIORITY', 'INSTRUME',
'CDELT1', 'CDELT2', 'JD', 'LST', 'POSANGLE', 'LATITUDE', 'LONGITUD', 'ELEVATIO', 'AZIMUTH',
'HA', 'RAEOD', 'DECEOD', 'RA', 'DEC', 'OBJRA', 'OBJDEC', 'EPOCH', 'EQUINOX', 'CAMTEMP',
'FOCUSPOS', 'AIRMASS', 'RAWISTP', 'WXTEMP', 'WXPRES', 'WXWNDSPD', 'WXWNDDIR', 'WXHUMID', 'FWHMH', 'FWHMHS', 'FWHMV', 'FWHMVS']

TOKENS_NOTUSED = ['SIMPLE', 'BITPIX', 'NAXIS', 'NAXIS1', 'NAXIS2', 'OFFSET1', 'OFFSET2', 'XFACTOR',
'YFACTOR', 'RAWHENC', 'RAWDENC', 'RAWOSTP', 'HCOMSCAL', 'HCOMSTAT']

class MainWindow(wx.Frame):
	def __init__(self, filename='noname.txt'):
		super(MainWindow, self).__init__(None)
		super(MainWindow, self).SetTitle('FITS Hydra')
		_icon = wx.Icon('fits_hydra.ico', wx.BITMAP_TYPE_ICO)
		self.SetIcon(_icon)
		self.SetSize((700,500))

		self.hdrs = {}
		self.paths = []
		self.lastdir = ''

		self.gr = grid.Grid(self)
		self.gr.CreateGrid(0,1)
		self.gr.SetColLabelValue(0,'File')
		self.gr.SetRowLabelSize(0)
		self.gr.SetSelectionMode(1) # should set row selection

		self.toks = wx.Menu()
		k=1
		for i in range(len(TOKENS_LIST)):
			item = self.toks.Append(wx.ID_ANY, TOKENS_LIST[i], kind=wx.ITEM_CHECK)
			self.Bind(wx.EVT_MENU, self.onToggle, item)
			self.gr.SetColLabelValue(i+1, TOKENS_LIST[i])
			if TOKENS_LIST[i] in DEFAULT_TOKENS:
				item.Check()
				self.gr.AppendCols(1)
				self.gr.SetColLabelValue(k, TOKENS_LIST[i])
				k+=1
			if (i+1) % 25 == 0:
				self.toks.Break()
				
		fileMenu = wx.Menu()
		tmp = fileMenu.Append(wx.ID_ANY,'x')
		tmp.SetBitmap(wx.EmptyBitmap(1,1)) # trick to handle menu bitmaps bug
		item = fileMenu.Append(wx.ID_OPEN, '&Open\tCtrl+O', 'Load FITS headers from file(s)')
		item.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN))
		fileMenu.Remove(tmp.GetId())
		self.Bind(wx.EVT_MENU, self.onOpen, item)
		item = fileMenu.Append(wx.ID_ANY, '&Rename..', 'Rename selected files based on header information')
		self.Bind(wx.EVT_MENU, self.onRename, item)
		item = fileMenu.Append(wx.ID_EXIT, 'E&xit\tCtrl+Q', 'Exit the program')
		item.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_QUIT))
		self.Bind(wx.EVT_MENU, self.onExit, item)
		editMenu = wx.Menu()
		item = editMenu.Append(wx.ID_ANY, 'Select &All\tCtrl+A', 'Copy Selection to Clipboard')
		self.Bind(wx.EVT_MENU, self.onSelectAll, item)
		item = editMenu.Append(wx.ID_COPY, '&Copy\tCtrl+C', 'Copy Selection to Clipboard')
		self.Bind(wx.EVT_MENU, self.onCopy, item)
		item = editMenu.Append(wx.ID_ANY, '&Clear\tDel', 'Clear Selection')
		self.Bind(wx.EVT_MENU, self.onClear, item)
		helpMenu = wx.Menu()
		tmp = helpMenu.Append(wx.ID_ANY,'x')
		tmp.SetBitmap(wx.EmptyBitmap(1,1)) # trick to handle menu bitmaps bug
		item = helpMenu.Append(wx.ID_ABOUT, '&About', 'About this program')
		item.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, size=(16,16)))
		helpMenu.Remove(tmp.GetId())
		self.Bind(wx.EVT_MENU, self.onAbout, item)

		menuBar = wx.MenuBar()
		menuBar.Append(fileMenu, '&File')
		menuBar.Append(editMenu, '&Edit')
		menuBar.Append(helpMenu, '&Help')
		self.SetMenuBar(menuBar)
		self.CreateStatusBar()

		for i in range(self.gr.GetNumberRows()):
			for j in range(self.gr.GetNumberCols()):
				self.gr.SetReadOnly(i,j,True)
		self.gr.Bind(grid.EVT_GRID_CMD_LABEL_RIGHT_CLICK, self.onRight, None)
		self.gr.Bind(grid.EVT_GRID_CMD_LABEL_LEFT_CLICK, self.onLeft, None)
		
		self.retag = RetagDialog(self)
		self.retag.Show(False)
		
	def IsChecked(self, tok):
		for item in self.toks.GetMenuItems():
			if item.GetItemLabelText() == tok:
				return item.IsChecked()
		return False

	def findColumn(self, tok):
		for i in range(self.gr.GetNumberCols()):
			if self.gr.GetColLabelValue(i) == tok:
				return i
		return -1
		
	def showColumn(self, tok):
		k = self.gr.GetNumberCols()
		self.gr.AppendCols(1)
		self.gr.SetColLabelValue(k,tok)
		for i in range(self.gr.GetNumberRows()):
			if i<len(self.paths):
				j = TOKENS_LIST.index(tok)
				self.gr.SetCellValue(i,k,self.hdrs[self.paths[i]][j])
				self.gr.SetReadOnly(i,k)
		self.gr.AutoSizeColumn(k)
		self.gr.ClearSelection()
		
	def hideColumn(self, tok):
		save_labels=[]
		for i in range(self.gr.GetNumberCols()):
			label = self.gr.GetColLabelValue(i)
			if label == tok:
				k=i
				continue
			else:
				save_labels.append(label)
		if 'k' in locals():
			self.gr.DeleteCols(k)
			for i in range(len(save_labels)):
				self.gr.SetColLabelValue(i,save_labels[i])
		
				
	def sortByColumn(self, n):
		sorter={}
		for i in range(len(self.paths)):
			sorter[self.paths[i]] = self.gr.GetCellValue(i,n)
		paths = sorted(sorter, key=lambda k: (sorter[k], k))			
		info = [self.hdrs[path] for path in paths]
		self.gr.DeleteRows(0,self.gr.GetNumberRows())
		self.hdrs = {}
		self.paths = []
		for path,info in zip(paths,info):
			self.addRow(path, info)
	
	def addRow(self, path, info_list):
		for i in range(self.gr.GetNumberRows()):
			if self.gr.GetCellValue(i,0) == '':
				n=i
				break
		else:
			n=self.gr.GetNumberRows()
			self.gr.AppendRows(1)
		self.hdrs[path]=info_list
		self.paths.append(path)
		self.gr.SetCellValue(n,0,os.path.basename(path))
		self.gr.SetReadOnly(n,0)
		for i in range(len(info_list)):
			k = self.findColumn(TOKENS_LIST[i])
			if k>0:
				self.gr.SetCellValue(n,k,info_list[i])
				self.gr.SetReadOnly(n,k)
				
	def GetSelection(self):
		sel=[]
		top = self.gr.GetSelectionBlockTopLeft()
		bottom = self.gr.GetSelectionBlockBottomRight()
		for (r1,c1),(r2,c2) in zip(top,bottom):
			sel += [r1+x for x in range(r2-r1+1)]
		return sorted(sel)

	def onOpen(self, event):
		wildcard = "FITS image files (*.fts,*.fits,*.fit)|*.fts;*.fits;*.fit"
		dialog = wx.FileDialog(None, "Choose a file", defaultDir=self.lastdir, wildcard=wildcard, style=wx.FD_OPEN|wx.FD_MULTIPLE)
		if dialog.ShowModal() == wx.ID_OK:
			for path in dialog.GetPaths():
				if path in self.hdrs.keys(): continue
				hdr = pyfits.getheader(path)
				info = []
				for tok in TOKENS_LIST:
					info.append( "%s" % hdr.get(tok, '') )
				self.addRow(path, info)
				self.lastdir = os.path.dirname(path)
			self.gr.AutoSizeColumns()
		dialog.Destroy()
		
	def onRename(self, event):
		if self.gr.GetNumberRows()<1: return
		rn = {}
		sel = self.GetSelection()
		if sel == []:
			self.gr.SelectAll()
			sel = self.GetSelection()
		for i in sel:
			if i<len(self.paths):
				f = self.paths[i]
				rn[f] = self.hdrs[f]
		self.retag.rn = rn
		self.retag.lastdir = os.path.dirname(self.paths[sel[0]])
		if self.retag.outdir.GetValue() == '':
			self.retag.outdir.SetValue(self.retag.lastdir)
		self.retag.update_sample(None)
		if self.retag.ShowModal() == wx.ID_OK:
			try:
				for oldf,newf in self.retag.filter_files():
					shutil.copy(oldf,newf)
					k = self.paths.index(oldf)
					self.paths[k] = newf
					self.hdrs[newf]=self.hdrs[oldf]
					del self.hdrs[oldf]
					if os.access(oldf,os.W_OK):
						os.remove(oldf)
					self.gr.SetCellValue(k,0,os.path.basename(newf))
					self.gr.SetReadOnly(k,0)
			except OSError as e:
				msg = 'File renaming failed!\n%s' % e
				errdialog=wx.MessageDialog(self, msg, 'Error', style=wx.OK|wx.ICON_ERROR)
				errdialog.ShowModal()
			self.gr.AutoSizeColumns()

	def onSelectAll(self, event):
		self.gr.SelectAll()
	
	def onCopy(self, event):
		t = ''
		for i in self.GetSelection():
			for k in range(self.gr.GetNumberCols()):
				t+=self.gr.GetCellValue(i,k)+'\t'
			t+=os.linesep
		if t=='':return
		wx.TheClipboard.Open()
		wx.TheClipboard.SetData(wx.TextDataObject(t))
		wx.TheClipboard.Close()

	def onClear(self, event):
		for i in reversed(self.GetSelection()):
			self.gr.DeleteRows(i)
			if i<len(self.paths):
				del self.hdrs[self.paths[i]]
				del self.paths[i]
		self.gr.ClearSelection()
		
	def onExit(self, event):
		self.Destroy()
		
	def onRight(self, event):
		if event.GetRow()<0:
			self.PopupMenu(self.toks)
			
	def onLeft(self, event):
		if event.GetRow()<0:
			self.sortByColumn(event.GetCol())
			
	def onToggle(self, event):
		id = event.GetId()
		item = self.toks.FindItemById(id)
		tok = self.toks.GetLabelText(id)
		if item.IsChecked():
			self.showColumn(tok)
		else:
			self.hideColumn(tok)
		
	def onAbout(self, event):
		description = """Allows simple browsing and renaming of
FITS images based on header information.

Chop one off, two grow back!
"""
		info = wx.AboutDialogInfo()
		
		info.SetName('The FITS Hydra')
		info.SetVersion(VERSION_STR)
		info.SetDescription(description)
		info.SetCopyright('(C) 2013 Bill Peterson')
		info.SetWebSite('http://astro.physics.uiowa.edu/rigel')
		info.AddDeveloper('Dr. Bill Peterson (bill.m.peterson@gmail.com)')
		
		wx.AboutBox(info)
		return

class RetagDialog(wx.Dialog):
	def __init__(self, *args, **kw):
		super(RetagDialog, self).__init__(style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE, *args, **kw) 	
		self.SetTitle("Rename Files")
		self.SetSize((700,400))
		self.rn = {}
		self.lastdir = ''
		
		opt = ['']+TOKENS_LIST
		fmt = '{OBJECT}_{FILTER}_{EXPTIME}sec_{DATE-OBS[0:10]}.fts'
		self.t1 = wx.Choice(self, choices=opt)
		self.t2 = wx.Choice(self, choices=opt)
		self.t3 = wx.Choice(self, choices=opt)
		self.sep = wx.ComboBox(self, value='_', choices=[' ','_','-','.'])
		self.format = wx.TextCtrl(self, value=fmt)
		self.outdir = wx.TextCtrl(self)
		chdir = wx.Button(self, label='Choose')
		self.output = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)
		self.t1.SetSelection(1)
		self.t2.SetSelection(2)
		self.t3.SetSelection(3)
		
		ctrl = wx.GridBagSizer(vgap=5, hgap=5)
		ctrl.Add(wx.StaticText(self, label='FITS Header Tokens:'), pos=(0,1), span=(1,3), flag=wx.ALIGN_CENTER)
		ctrl.Add(wx.StaticText(self, label='Separator:'), pos=(0,4))
		ctrl.Add(self.t1, pos=(1,1))
		ctrl.Add(self.t2, pos=(1,2))
		ctrl.Add(self.t3, pos=(1,3))
		ctrl.Add(self.sep, pos=(1,4))
		ctrl.Add(wx.StaticText(self, label='Format:'), pos=(2,0), flag=wx.ALIGN_RIGHT)
		ctrl.Add(self.format, pos=(2,1), span=(1,4), flag=wx.EXPAND)
		ctrl.Add(wx.StaticText(self, label='Output Dir:'), pos=(3,0), flag=wx.ALIGN_RIGHT)
		ctrl.Add(self.outdir, pos=(3,1), span=(1,4), flag=wx.EXPAND)
		ctrl.Add(chdir, pos=(3,5))
		
		vbox = wx.BoxSizer(wx.VERTICAL)
		vbox.Add(ctrl, border=5, flag=wx.ALL|wx.ALIGN_CENTER)
		vbox.Add(wx.StaticText(self, label='Result:'), border=5, flag=wx.ALL|wx.ALIGN_CENTER)
		vbox.Add(self.output, border=10, proportion=1, flag=wx.ALL|wx.ALIGN_CENTER|wx.EXPAND)
		vbox.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL), flag=wx.ALL|wx.ALIGN_CENTER, border=5)
		self.SetSizer(vbox)
		
		self.t1.Bind(wx.EVT_CHOICE, self.update_format)
		self.t2.Bind(wx.EVT_CHOICE, self.update_format)
		self.t3.Bind(wx.EVT_CHOICE, self.update_format)
		self.sep.Bind(wx.EVT_TEXT, self.update_format)
		self.format.Bind(wx.EVT_TEXT, self.update_sample)
		self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
		chdir.Bind(wx.EVT_BUTTON, self.change_outdir, chdir)


	def onOK(self, event):
		confirm = wx.MessageDialog(self, 'Files will be permanently renamed! Proceed?',
			'Confirm', style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_EXCLAMATION)
		if confirm.ShowModal()==wx.ID_YES:
			self.EndModal(wx.ID_OK)
		else:
			self.EndModal(wx.ID_CANCEL)
			
	def change_outdir(self, event):
		dialog = wx.DirDialog(self, defaultPath=self.lastdir)
		if dialog.ShowModal()==wx.ID_OK:
			self.outdir.SetValue(dialog.GetPath())
		dialog.Destroy()
			
	def update_format(self, event):
		t1 = self.t1.GetStringSelection()
		t2 = self.t2.GetStringSelection()
		t3 = self.t3.GetStringSelection()
		sep = self.sep.GetValue()
		fields=[]
		if t1!='': fields.append('{%s}' % t1)
		if t2!='': fields.append('{%s}' % t2)
		if t3!='': fields.append('{%s}' % t3)
		self.format.SetValue(sep.join(fields)+'.fts')
		self.update_sample(None)

	def update_sample(self, event):
		self.output.Clear()
		for f,newf in self.filter_files():
			self.output.AppendText('%s -> %s\n' % (os.path.basename(f), os.path.basename(newf)) )
	
	def filter_files(self):
		fmt = self.format.GetValue()
		sep = self.sep.GetValue()
		fields = []
		oldf = self.rn.keys()
		newf = []
		for f in oldf:
			dir = self.outdir.GetValue()
			fname = fmt
			for (t,func) in re.findall('{([A-Z-]+)(.*?)}', fname):
				if t not in TOKENS_LIST: continue
				val = self.rn[f][TOKENS_LIST.index(t)]
				try:
					fname = re.sub( '{%s.*?}' % t, eval('val%s' % func) , fname )
				except:
					fname = re.sub( '{%s.*?}' % t, val, fname )
			fname = re.sub(':','-',fname)
			fname = os.path.join(dir,fname)
			froot = os.path.splitext(fname)[0]				
			k=1
			while os.path.exists(fname) or fname in newf:
				fname=froot+sep+'%03d.fts' % k
				k+=1
			newf.append( fname )
		return zip(oldf, newf)
		
app = wx.App(redirect=False)
frame = MainWindow()

frame.Show()
app.MainLoop()


