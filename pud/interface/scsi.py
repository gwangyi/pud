from . import Device, Command
from pysgutils import sg_pt, sg_lib, AlignedBuffer
import struct


class SCSIDevice(Device):
    command_fields = ['cdb', 'sense', 'sense_len', 'data_in_len', 'data_in', 'data_out', 'result']

    def __init__(self, path):
        self.path = path
        self._open_depth = 0
        self._device = None

        with self:
            sense = sg_lib.SCSISense(32)
            buffer = AlignedBuffer(572, alignment=4096)
            cmd = SCSICommand(cdb=("BBBHx", 0x12, 1, 0x89, 572),
                              sense=sense, data_in=buffer)
            try:
                cmd.send()
                ata_id = buffer[60:]
                serial = sg_lib.sg_ata_get_chars(ata_id, 10, 10)
                revision = sg_lib.sg_ata_get_chars(ata_id, 23, 4)
                model = sg_lib.sg_ata_get_chars(ata_id, 27, 20)
                vendor = b'ATA Device'
            except (sg_pt.SCSIError, sg_pt.TransportError, OSError):
                buffer.resize(96)
                cmd = SCSICommand(cdb=("BxxHx", 0x12, 96),
                                  sense=sense, data_in=buffer)
                cmd.send()
                vendor = buffer[8:16]
                model = buffer[16:32]
                revision = buffer[32:36]
                serial = buffer[36:44]

            buffer.resize(32)
            cmd = SCSICommand(cdb=("BBQLxx", 0x9e, 0x10, 0, 32),
                              sense=sense, data_in=buffer)
            try:
                cmd.send()
                capacity, sector_size = struct.unpack(">QL", buffer[:12])
            except (sg_pt.SCSIError, sg_pt.TransportError, OSError):
                capacity, sector_size = 0, 0

        super().__init__(path, vendor, model, revision, serial, capacity, sector_size)

    def _open(self):
        self._device = sg_pt.SCSIPTDevice(self.path, verbose=True)

    def _close(self):
        self._device.close()
        self._device = None

    def create_command(self, **kwargs):
        return SCSICommand(**kwargs)

    def send(self, command: 'SCSICommand'):
        command.pt_obj.do_scsi_pt(device=self._device, verbose=True)


class SCSICommand(Command):
    def __init__(self, cdb, sense=None, sense_len=None, data_in=None, data_out=None, data_in_len=None):
        self.pt_obj = sg_pt.SCSIPTObject()
        self.cdb = cdb
        if sense is None:
            if sense_len is not None:
                self.pt_obj.sense = sg_lib.SCSISense(sense_len)
            else:
                self.pt_obj.sense = sg_lib.SCSISense(32)
        else:
            self.pt_obj.sense = sense
        if data_in is None:
            if data_in_len is not None:
                self.pt_obj.data_in = AlignedBuffer(data_in_len, alignment=4096)
        else:
            self.pt_obj.data_in = data_in
        if data_out is not None:
            self.pt_obj.data_out = AlignedBuffer(data_out, len(data_out), alignment=4096)

    @property
    def cdb(self):
        return self.pt_obj.cdb

    @cdb.setter
    def cdb(self, cdb):
        if isinstance(cdb, tuple) and isinstance(cdb[0], str):
            self.pt_obj.cdb = sg_lib.SCSICommand.build(*cdb)
        else:
            self.pt_obj.cdb = sg_lib.SCSICommand(cdb)

    @property
    def sense(self):
        return self.pt_obj.sense

    @property
    def data_in(self):
        return self.pt_obj.data_in

    @property
    def data_out(self):
        return self.pt_obj.data_out


@Device.register_enumerator
def scsi_devices():
    pass
