#*********************************************************************
# content   = saves as
#             executes other scripts on PUBLISH (on task in file name)
# version   = 0.0.1
# date      = 2017-08-01
#
# license   = MIT
# copyright = Copyright 2017 Animationsinstitut
# author    = Alexander Richter <pipeline@richteralexander.com>
#*********************************************************************
# This source file has been developed within the scope of the
# Technical Director course at Filmakademie Baden-Wuerttemberg.
# http://td.animationsinstitut.de
#*********************************************************************

import os
import sys
import getpass
import datetime
from threading import Thread

from Qt import QtWidgets, QtGui, QtCore, QtCompat

import libLog
import libData
import libSnapshot
import libFunc
import arNotice

from tank import Tank
from users import User
from arUtil import ArUtil


#*********************************************************************
# VARIABLE
TITLE = os.path.splitext(os.path.basename(__file__))[0]
LOG   = libLog.init(script=TITLE)


#*********************************************************************
# CLASS
class ArSaveAs(ArUtil):
    def __init__(self, new_file=True):
        super(ArSaveAs, self).__init__()

        path_ui = ("/").join([os.path.dirname(__file__), "ui", TITLE + ".ui"])
        self.wgSaveAs = QtCompat.loadUi(path_ui)

        self.all_task = '<all tasks>'

        self.new_file  = new_file
        self.save_file = ''
        self.save_dir  = self.data['project']['path']
        self.software  = Tank().software.software
        self.inputs    = [self.wgSaveAs.cbxScene, self.wgSaveAs.cbxSet, self.wgSaveAs.cbxAsset, self.wgSaveAs.cbxTask]

        self.wgHeader.btnOption.hide()
        self.wgHeader.cbxAdd.hide()
        self.wgHeader.setWindowIcon(QtGui.QIcon(libData.get_img_path("btn/btnSave48")))

        btn_title = TITLE if self.new_file else 'Create New Folder'
        self.wgHeader.setWindowTitle(btn_title)
        btn_title = 'Save As' if self.new_file else 'Create'
        self.wgHeader.btnAccept.setText(btn_title)
        self.wgHeader.layMain.addWidget(self.wgSaveAs, 0, 0)
        self.resize_widget(self.wgSaveAs)

        # self.wgSaveAs : always on top
        self.wgSaveAs.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        self.setup()
        self.wgSaveAs.show()
        LOG.info('START : arSaveAs')


    #*********************************************************************
    # SETUP
    def setup(self):
        self.wgSaveAs.cbxScene.clear()
        self.wgSaveAs.cbxSet.clear()
        self.wgSaveAs.cbxAsset.clear()
        self.wgSaveAs.lblStatus.clear()
        self.set_open_folder(self.save_dir)
        self.wgHeader.edtComment.setText('PROJECT PATH: ' + self.save_dir)

        self.wgSaveAs.cbxScene.currentIndexChanged.connect(self.change_cbxScene)
        self.wgSaveAs.cbxTask.currentIndexChanged.connect(self.update_file)
        self.wgSaveAs.cbxAsset.editTextChanged.connect(self.update_file)

        for keys, items in self.data['rules']['SCENES'].items():
            self.wgSaveAs.cbxScene.addItem(keys)

        self.update_file()


    #*********************************************************************
    # PRESS
    def press_btnAccept(self):
        if self.create_folder_structure() and self.new_file:
            self.wgHeader.close()


    #*********************************************************************
    # CHANGE
    def change_cbxScene(self):
        self.wgSaveAs.cbxTask.clear()
        if not self.new_file: self.wgSaveAs.cbxTask.addItem(self.all_task)

        self.scene_steps = len(self.data['rules']['SCENES'][self.wgSaveAs.cbxScene.currentText()].split('/'))
        if self.scene_steps < 5:
            self.wgSaveAs.cbxSet.hide()
            self.wgSaveAs.lblSet.hide()
        else:
            self.wgSaveAs.cbxSet.show()
            self.wgSaveAs.cbxSet.clear()
            self.wgSaveAs.lblSet.show()

        try:
            if self.wgSaveAs.cbxScene.currentText():
                self.wgSaveAs.cbxTask.addItems(self.data['rules']['TASK'][self.wgSaveAs.cbxScene.currentText()])
        except: self.set_status('FAILED adding tasks items: data/project/$project/rules.yml : TASK', msg_type=3)

        if self.software == 'nuke':
            index = self.wgSaveAs.cbxTask.findText('COMP', QtCore.Qt.MatchContains)
            if index >= 0: self.wgSaveAs.cbxTask.setCurrentIndex(index)

        try:
            self.save_dir = self.data['project']['PATH'][self.wgSaveAs.cbxScene.currentText()]
            if self.wgSaveAs.cbxSet.isVisible():
                self.wgSaveAs.cbxSet.addItems(libFunc.get_file_list(self.save_dir))
        except: LOG.error('FAILED adding PATH items: data/project/$project/project.yml : PATH', exc_info=True)


    #*********************************************************************
    # FUNC
    def update_file(self):
        if self.wgSaveAs.cbxScene.currentText():
            status_text = '/' + self.data['rules']['STATUS']['work']
            if self.new_file: extension = Tank().software.extension
            else: extension = ''
            new_item = self.data['rules']['SCENES'][self.wgSaveAs.cbxScene.currentText()]
            new_item = new_item.format(set       = self.wgSaveAs.cbxSet.currentText(),
                                       asset     = self.wgSaveAs.cbxAsset.currentText(),
                                       task      = self.wgSaveAs.cbxTask.currentText(),
                                       status    = self.data['rules']['STATUS']['work'],
                                       version   = self.data['rules']['FILE']['version'].replace(r'\d','0').replace('_',''),
                                       user      = getpass.getuser()[:2].lower(),
                                       extension = extension,
                                       frame     = self.data['rules']['start_frame'])

            if self.new_file: status_text += '/' + os.path.basename(new_item)
            self.save_file = self.save_dir + '/' + new_item

            self.wgSaveAs.lblStatus.setText(status_text)


    def create_folder_structure(self):
        # CHECK inputs
        for inputs in self.inputs:
            if not inputs.currentText():
                if self.scene_steps < 5 and self.wgSaveAs.cbxSet == inputs: continue
                self.set_status('Missing input: {}'.format(inputs.objectName().replace('cbx', '')), msg_type=2)
                return False

        self.update_file()

        # CHECK FILE
        if os.path.exists(self.save_file):
            self.set_status('PATH already exists: {}'.format(self.save_file), msg_type=2)
            return False

        save_list = []

        if self.all_task in self.save_file:
            for task in self.data['rules']['TASK'][self.wgSaveAs.cbxScene.currentText()]:
                new_path = self.save_file.replace(self.all_task, task)
                save_list.append(new_path)
        else: save_list.append(self.save_file)

        LOG.debug('Folder list {}'.format(save_list))
        for folder in save_list: libFunc.create_folder(folder)

        if self.new_file:
            Tank().software.scene_saveAs(self.save_file, setup_scene=True)
            libSnapshot.create_any_screenshot(self.wgSaveAs)
            tmp_img_path = libSnapshot.save_snapshot(self.save_file)

            tmp_title = os.path.basename(self.save_file).split('.')[0]
            tmp_func = 'SAVE AS'

            self.set_meta_data(self.save_file)
        else:
            try:    self.set_open_folder(save_list[0])
            except: LOG.error('CANT set folder: {}'.format(save_list))
            self.set_status('Created new {}'.format(self.wgSaveAs.cbxScene.currentText()), msg_type=1)

            tmp_img_path = 'lbl/lblCreate131'
            tmp_title = self.wgSaveAs.cbxScene.currentText()
            tmp_func = 'CREATE'

        note = arNotice.Notice(title  = tmp_title,
                               msg    = 'CREATED a new {} with folders'.format(self.wgSaveAs.cbxScene.currentText()),
                               func   = tmp_func,
                               img    = tmp_img_path,
                               img_link = os.path.dirname(self.save_file))
        arNotice.ArNotice(note)

        return True

    def set_meta_data(self, save_path=''):
        meta_path    = os.path.dirname(save_path) + libData.META_INFO
        comment_dict = {'user':    User().id,
                        'comment': 'new scene'}
        libData.set_data(meta_path, os.path.basename(save_path), comment_dict)


def create():
    app = QtWidgets.QApplication(sys.argv)
    main_window = ArSaveAs()
    sys.exit(app.exec_())


def start(new_file=True):
    global main_widget
    main_widget = ArSaveAs(new_file)

# create()
