class HumansError(Exception):
    pass


class EmailAlreadyRegistered(HumansError):
    pass


class HumanNotFound(HumansError):
    pass


class RegistrationNotVerified(HumansError):
    pass
