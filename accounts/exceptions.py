class AccountsError(Exception):
    pass


class EmailNotRegistered(AccountsError):
    pass


class VerificationError(AccountsError):
    pass


class VerificationNotFound(VerificationError):
    pass


class VerificationPurposeMismatch(VerificationError):
    pass


class VerificationExpired(VerificationError):
    pass


class VerificationAlreadyUsed(VerificationError):
    pass


class VerificationAttemptsExceeded(VerificationError):
    pass


class InvalidVerificationCode(VerificationError):
    pass


class VerificationUserNotFound(AccountsError):
    pass
