package auth

import "testing"

func TestStaticLoginAuthenticatorAuthenticate(t *testing.T) {
	authenticator := NewStaticLoginAuthenticator([]StaticCredential{
		{
			Account:  "SpotTruth_User",
			Password: "user-pass",
			UserID:   "u-1",
			Username: "alice",
			Role:     RoleUser,
		},
	})

	principal, ok := authenticator.Authenticate("spottruth_user", "user-pass")
	if !ok {
		t.Fatal("期望鉴权成功")
	}
	if principal.UserID != "u-1" {
		t.Fatalf("UserID 不符合预期: %s", principal.UserID)
	}
	if principal.Role != RoleUser {
		t.Fatalf("Role 不符合预期: %s", principal.Role)
	}
}

func TestStaticLoginAuthenticatorRejectInvalidCredential(t *testing.T) {
	authenticator := NewStaticLoginAuthenticator([]StaticCredential{
		{
			Account:  "spottruth_user",
			Password: "user-pass",
			UserID:   "u-1",
			Username: "alice",
			Role:     RoleUser,
		},
	})

	if _, ok := authenticator.Authenticate("spottruth_user", "wrong-pass"); ok {
		t.Fatal("密码错误时不应通过")
	}
	if _, ok := authenticator.Authenticate("not-exist", "user-pass"); ok {
		t.Fatal("不存在账号时不应通过")
	}
}

func TestStaticLoginAuthenticatorSkipInvalidConfig(t *testing.T) {
	authenticator := NewStaticLoginAuthenticator([]StaticCredential{
		{
			Account:  "",
			Password: "pass",
			UserID:   "u-1",
			Role:     RoleUser,
		},
		{
			Account:  "demo",
			Password: "",
			UserID:   "u-2",
			Role:     RoleUser,
		},
		{
			Account:  "demo2",
			Password: "pass",
			UserID:   "",
			Role:     RoleUser,
		},
		{
			Account:  "demo3",
			Password: "pass",
			UserID:   "u-3",
			Role:     Role("guest"),
		},
	})

	if _, ok := authenticator.Authenticate("demo", "pass"); ok {
		t.Fatal("非法配置不应被接受")
	}
}
