package auth

import "strings"

type Principal struct {
	UserID   string
	Username string
	Role     Role
}

type LoginAuthenticator interface {
	Authenticate(account, password string) (Principal, bool)
}

type StaticCredential struct {
	Account  string
	Password string
	UserID   string
	Username string
	Role     Role
}

type StaticLoginAuthenticator struct {
	credentials map[string]StaticCredential
}

func NewStaticLoginAuthenticator(raw []StaticCredential) *StaticLoginAuthenticator {
	credentials := make(map[string]StaticCredential)
	for _, item := range raw {
		account := normalizeAccount(item.Account)
		if account == "" || strings.TrimSpace(item.Password) == "" || strings.TrimSpace(item.UserID) == "" || !isValidRole(item.Role) {
			continue
		}
		if strings.TrimSpace(item.Username) == "" {
			item.Username = item.Account
		}
		credentials[account] = item
	}
	return &StaticLoginAuthenticator{credentials: credentials}
}

func (a *StaticLoginAuthenticator) Authenticate(account, password string) (Principal, bool) {
	if a == nil {
		return Principal{}, false
	}
	credential, ok := a.credentials[normalizeAccount(account)]
	if !ok {
		return Principal{}, false
	}
	if credential.Password != strings.TrimSpace(password) {
		return Principal{}, false
	}
	return Principal{
		UserID:   credential.UserID,
		Username: credential.Username,
		Role:     credential.Role,
	}, true
}

func normalizeAccount(account string) string {
	return strings.ToLower(strings.TrimSpace(account))
}
