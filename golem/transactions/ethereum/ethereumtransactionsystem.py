import logging
from time import sleep

from ethereum.utils import privtoaddr

from golem.ethereum import Client
from golem.ethereum.paymentprocessor import PaymentProcessor
from golem.report import report_calls, Component
from golem.transactions.ethereum.ethereumincomeskeeper \
    import EthereumIncomesKeeper
from golem.transactions.transactionsystem import TransactionSystem
from golem.utils import encode_hex

log = logging.getLogger('golem.pay')


class EthereumTransactionSystem(TransactionSystem):
    """ Transaction system connected with Ethereum """

    def __init__(self, datadir, account_password: bytes, port=None):
        """ Create new transaction system instance for node with given id
        :param account_password bytes: password for Ethereum account
        """
        super(EthereumTransactionSystem, self).__init__(
            incomes_keeper_class=EthereumIncomesKeeper
        )

        self.__eth_node = self.incomes_keeper.eth_node = Client(datadir, port)
        payment_processor = PaymentProcessor(
            self.__eth_node,
            account_password,
            faucet=True
        )
        self.__proc = self.incomes_keeper.processor = payment_processor
        self.__proc.start()

    def stop(self):
        if self.__proc.running:
            self.__proc.stop()
        if self.__eth_node.node is not None:
            self.__eth_node.node.stop()

    def add_payment_info(self, *args, **kwargs):
        payment = super(EthereumTransactionSystem, self).add_payment_info(
            *args,
            **kwargs
        )
        self.__proc.add(payment)
        return payment

    def get_payment_address(self):
        """ Human readable Ethereum address for incoming payments."""
        return '0x' + self.__proc.account.address.hex()

    def get_balance(self):
        if not self.__proc.balance_known():
            return None, None, None
        gnt = self.__proc.gnt_balance()
        av_gnt = self.__proc._gnt_available()
        eth = self.__proc.eth_balance()
        return gnt, av_gnt, eth

    @report_calls(Component.ethereum, 'sync')
    def sync(self):
        syncing = True
        while syncing:
            try:
                syncing = self.__eth_node.is_syncing()
            except Exception as e:
                log.error("IPC error: {}".format(e))
                syncing = False
            else:
                sleep(0.5)
