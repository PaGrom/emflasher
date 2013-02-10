# -*- coding: utf-8 -*-

import sys
import os
import shutil
import serial
import time
import argparse


class Emflasher:
    """
    Script for the base firmware embedded systems
    """

    def __init__(self):
        self.serial = serial.Serial()

        self.parse_args()           # парсер аргументов командной строки
        self.connect_to_serial()    # получение доступа к серийному порту
        self.connect_to_uboot()     # вход в командную строку u-boot

        self.set_tftp_settings()    # установка ip-адреса tftp-сервера

        self.flash_uboot()          # прошивка u-boot в nand
        self.flash_kernel()         # прошивка linux kernel в nand
        self.split_rootfs()         # разбивает rootfs на части, так как образ не помещается в RAM целиком
        self.flash_rootfs()         # прошивка rootfs в nand

        self.beep()
        sys.stdout.write("Done!\n")

    def parse_args(self):
        """
        Метод парсит аргументы командной строки и сохраняет основные параметры
        """

        parser = argparse.ArgumentParser()

        parser.add_argument('-p', '--port', action='store', dest='port',
            help='Serial port', default='/dev/ttyS0')
        parser.add_argument('-b', '--baudrate', action='store', dest='baudrate',
            help='Serial baudrate', default=115200)
        parser.add_argument('-t', '--timeout', action='store', dest='timeout',
            help='Serial timeout', default=1)
        parser.add_argument('-bs', '--bytesize', action='store',
            dest='bytesize', help='Serial bytesize', default=8)

        parser.add_argument('-ia', '--ipaddr', action='store', dest='ipaddr',
            help='TFTP IP addr', default='192.168.0.32')
        parser.add_argument('-si', '--serverip', action='store',
            dest='serverip', help='TFTP Server IP addr', default='192.168.0.23')
        parser.add_argument('-tf', '--tftp_folder', action='store',
            dest='tftp_folder', help='TFTP folder addr', default='/tftpboot')

        parser.add_argument('-ais', '--aisfile', action='store', dest='aisfile',
            help='AIS file of U-Boot', default='u-boot_working.ais')
        parser.add_argument('-k', '--kernel', action='store', dest='kernel',
            help='Kernel Image', default='uImage')
        parser.add_argument('-r', '--rootfs', action='store', dest='rootfs',
            help='Rootfs file', default='rootfs-promsd-v2.jffs2')

        parser.add_argument('-ns', '--not_by_symbols', action='store_true',
            help='write not by symbols')

        args = parser.parse_args()
        self.serial.port = args.port
        self.serial.baudrate = args.baudrate
        self.serial.timeout = args.timeout
        self.serial.bytesize = args.bytesize

        self.tftp_ipaddr = args.ipaddr
        self.tftp_serverip = args.serverip
        self.tftp_folder = args.tftp_folder

        self.ais_file = args.aisfile
        self.kernel = args.kernel
        self.rootfs = args.rootfs

        self.not_by_symbols = args.not_by_symbols

    def connect_to_serial(self):
        """
        Метод для соединения с MAK-4M по серийному порту
        """

        sys.stdout.write("Соединение с серийным портом...\n")

        try:
            self.serial.open()
        except serial.SerialException:
            sys.stderr.write("Не удается открыть порт %s.\n"
                % self.serial.port)
            sys.exit(1)

        sys.stdout.write("Соединение с портом %s установлено.\n"
            % self.serial.port)

        # self.read_from_serial(10000)

    def write_to_serial(self, input_str, timeout = 0.05):
        """
        Метод для записи в serial.
        Если by_symbols == False, строка записывается сразу,
        если True, то посимвольно с таймаутом (по умолчанию 0.25 секунд)
        """

        sys.stdout.write("Write to serial ---> " + input_str)

        if not self.not_by_symbols:
            for i in input_str:
                self.serial.write(i)
                time.sleep(timeout)
        else:
            self.serial.write(input_str)

    def read_from_serial(self, number):
        """
        Метод читает из serial заданное кол-во символов
        """

        out_string = self.serial.read(number)

        sys.stdout.write("\n//-----------------------------------------------------\n")
        sys.stdout.write(out_string)
        sys.stdout.write("\n\\\\-----------------------------------------------------\n\n")

        return out_string

    def write_and_wait_complete(self, input_str, test_str, error_str, timeout = 1):
        """
        Метод пишет команду в serial и ждет успешного выполнения
        """

        out_string = ''
        full_time = 0
        count = 10

        self.write_to_serial(input_str)

        while True:
            if count == 0:
                raise Exception(error_str + 'за %d сек\n\n' % full_time)
            time.sleep(timeout)
            full_time += timeout
            out_string += self.read_from_serial(10000)
            if out_string.find(test_str) == -1:
                count -= 1
                continue
            else:
                break

        sys.stdout.write("Операция '%s' заверешена успешно за %d сек\n\n" % (input_str, full_time))

        return out_string

    def connect_to_uboot(self):
        """
        Метод для входа в интерфейс U-Boot
        """

        sys.stdout.write("""Если UBoot загружен из FLASH, то перезагрузите MAK-4M перед тем, как нажать клавишу Enter. (при перезагрузке нажмите Enter без промдлений)\n""")
        raw_input("Press Enter")
        sys.stdout.write("Соединение с U-boot...\n")
        time.sleep(5)
        self.serial.write('s')  # anykey
        time.sleep(1)
        self.serial.write('\x03')  # interrupt (Ctrl + C)
        time.sleep(1)

        out_string = self.read_from_serial(10000)
        if out_string.find("U-Boot >") == -1:
            raise Exception("Соединение с U-boot не установлено. Попробуйте еще раз.\n")

    def set_tftp_settings(self):
        """
        Метод устанавливает ip-адреса tftp-сервера
        """

        input_str = "setenv ipaddr %s\n" % self.tftp_ipaddr
        self.write_to_serial(input_str)
        time.sleep(2)
        self.read_from_serial(10000)
        input_str = "setenv serverip %s\n" % self.tftp_serverip
        self.write_to_serial(input_str)
        time.sleep(2)
        self.read_from_serial(10000)

    def flash_uboot(self):
        """
        Прошивка uboot в NAND
        """

        sys.stdout.write("Скачивание AIS файла...\n")
        input_str = "tftp %s\n" % self.ais_file
        test_str = "Bytes transferred"
        error_str = "Не удается скачать AIS файл "
        self.write_and_wait_complete(input_str, test_str, error_str)

        sys.stdout.write("Erasing nand...\n")
        input_str = "nand erase 0x20000 0x40000\n"
        test_str = "100% complete"
        error_str = "Операция %s не была завершена успешно " % input_str
        self.write_and_wait_complete(input_str, test_str, error_str)

        sys.stdout.write("Write nand...\n")
        input_str = "nand write.e 0xc0700000 0x20000 0x40000\n"
        test_str = "bytes written: OK"
        error_str = "Операция %s не была завершена успешно " % input_str
        self.write_and_wait_complete(input_str, test_str, error_str)

    def flash_kernel(self):
        """
        Прошивка kernel в NAND
        """

        sys.stdout.write("Скачивание образа...\n")
        input_str = "tftp %s\n" % self.kernel
        test_str = "Bytes transferred"
        error_str = "Не удается скачать образ "
        self.write_and_wait_complete(input_str, test_str, error_str)

        sys.stdout.write("Erasing nand...\n")
        input_str = "nand erase 0x80000 0x400000\n"
        test_str = "100% complete"
        error_str = "Операция %s не была завершена успешно " % input_str
        self.write_and_wait_complete(input_str, test_str, error_str)

        sys.stdout.write("Write nand...\n")
        input_str = "nand write.e 0xc0700000 0x80000 0x400000\n"
        test_str = "bytes written: OK"
        error_str = "Операция %s не была завершена успешно " % input_str
        self.write_and_wait_complete(input_str, test_str, error_str)

    def split_rootfs(self):
        """
        Метод разбивает rootfs на части, так как образ не помещается в RAM целиком
        """

        sys.stdout.write("Скачивание %s...\n" % self.rootfs)
        shutil.copy(os.path.join(self.tftp_folder, self.rootfs), os.path.abspath(os.path.curdir))
        sys.stdout.write("Скачивание завершено.\n")

        file = open(self.rootfs, 'rb')
        data = file.read()
        file.close()

        sys.stdout.write("Разбивка %s на несколько частей...\n" % self.rootfs)

        bytes = len(data)
        self.inc = 0x400000
        self.count = 0
        self.parts_names = []
        self.parts_sizes = []

        for i in range(0, bytes + 1, self.inc):
            part_name = "%s_part_%s" % (self.rootfs, self.count)
            self.parts_names.append(part_name)
            f = open(part_name, 'wb')
            self.parts_sizes.append(hex(len(data[i:i + self.inc])))
            f.write(data[i:i + self.inc])
            self.count += 1
            f.close()
            sys.stdout.write("Закачиваю %s в %s...\n" % (part_name, self.rootfs))
            shutil.copy(part_name, self.tftp_folder)

        # print self.parts_sizes
        # print self.parts_names

    def flash_rootfs(self):
        """
        Прошивка rootfs в NAND
        """

        # self.parts_sizes = ['0x400000', '0x400000', '0x400000', '0x400000', '0x400000', '0x400000', '0x400000', '0x400000', '0x400000', '0x400000', '0x20000']
        # self.parts_names = ['rootfs-promsd-v2.jffs2_part_0', 'rootfs-promsd-v2.jffs2_part_1', 'rootfs-promsd-v2.jffs2_part_2', 'rootfs-promsd-v2.jffs2_part_3', 'rootfs-promsd-v2.jffs2_part_4', 'rootfs-promsd-v2.jffs2_part_5', 'rootfs-promsd-v2.jffs2_part_6', 'rootfs-promsd-v2.jffs2_part_7', 'rootfs-promsd-v2.jffs2_part_8', 'rootfs-promsd-v2.jffs2_part_9', 'rootfs-promsd-v2.jffs2_part_10']

        self.count = 11
        self.inc = 0x400000

        self.bad_blocks_count = 0   # счетчик bad block'ов. Каждый bad block смещает адрес памяти для записи rootfs на 128К (0x20000)

        sys.stdout.write("Erasing nand...\n")
        input_str = "nand erase 0x480000 0x7b00000\n"
        test_str = "100% complete"
        error_str = "Операция %s не была завершена успешно " % input_str
        self.write_and_wait_complete(input_str, test_str, error_str)

        for i in range(self.count):

            sys.stdout.write("Загружаю часть %d rootfs...\n" % i)
            input_str = "tftp 0xc0700000 %s\n" % self.parts_names[i]
            test_str = "Bytes transferred"
            error_str = "Не удалось скачать часть %d rootfs " % i
            self.write_and_wait_complete(input_str, test_str, error_str)

            sys.stdout.write("Write nand...\n")
            input_str = "nand write.e 0xc0700000 %s %s\n" % (hex(0x480000 + self.inc * i + self.bad_blocks_count * 0x20000), self.parts_sizes[i])
            test_str = "bytes written: OK"
            error_str = "Операция %s не была завершена успешно " % input_str
            out_string = self.write_and_wait_complete(input_str, test_str, error_str)

            bad_blocks = out_string.count('bad block')
            sys.stdout.write("Найдено bad block'ов: %d\n" % bad_blocks)

            self.bad_blocks_count += bad_blocks

    def beep(self):
        """
        Гудок, чтобы разбудить оператора
        """

        os.system('aplay beep.wav 2> /dev/null')


def main():
    Emflasher()


if __name__ == '__main__':
    main()
