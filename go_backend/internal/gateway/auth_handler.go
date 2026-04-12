package gateway

import (
	"encoding/json"
	"net/http"
	"time"

	"spottruth/go_backend/internal/auth"
	"spottruth/go_backend/internal/middleware"
)

type loginRequest struct {
	Account   string `json:"account"`
	Password  string `json:"password"`
	LoginType string `json:"login_type"`
}

type loginData struct {
	AccessToken string        `json:"access_token"`
	TokenType   string        `json:"token_type"`
	ExpiresIn   int64         `json:"expires_in"`
	User        loginUserData `json:"user"`
}

type loginUserData struct {
	ID       string    `json:"id"`
	Username string    `json:"username"`
	Role     auth.Role `json:"role"`
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, r *http.Request, status int, code, message, details string) {
	writeJSON(w, status, map[string]any{
		"code":    code,
		"message": message,
		"error": map[string]string{
			"type":    authErrorType(status),
			"details": details,
		},
		"request_id": middleware.GetRequestID(r),
		"timestamp":  time.Now().Format(time.RFC3339),
	})
}

func authErrorType(status int) string {
	switch status {
	case http.StatusUnauthorized:
		return "unauthorized"
	case http.StatusForbidden:
		return "forbidden"
	default:
		return "bad_request"
	}
}

func logoutHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// 清除 cookie（设置过期时间为过去）
		http.SetCookie(w, &http.Cookie{
			Name:     "access_token",
			Value:    "",
			Path:     "/",
			HttpOnly: true,
			Secure:   false,
			SameSite: http.SameSiteLaxMode,
			MaxAge:   -1,
			Expires:  time.Unix(0, 0),
		})

		writeJSON(w, http.StatusOK, map[string]any{
			"code":       "OK",
			"message":    "logout success",
			"request_id": middleware.GetRequestID(r),
			"timestamp":  time.Now().Format(time.RFC3339),
		})
	}
}

func loginHandler(tokenManager *auth.TokenManager, authenticator auth.LoginAuthenticator) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if tokenManager == nil || authenticator == nil {
			writeError(w, r, http.StatusInternalServerError, "INTERNAL_ERROR", "登录服务未配置", "token manager 或 login authenticator 为空")
			return
		}

		var req loginRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeError(w, r, http.StatusBadRequest, "REQUEST_INVALID", "请求体格式错误", "body 必须为合法 JSON")
			return
		}

		if req.Account == "" || req.Password == "" {
			writeError(w, r, http.StatusBadRequest, "REQUEST_INVALID", "账号或密码不能为空", "account/password 不能为空")
			return
		}

		if req.LoginType != "" && req.LoginType != "password" {
			writeError(w, r, http.StatusBadRequest, "REQUEST_INVALID", "暂不支持该登录方式", "login_type 仅支持 password")
			return
		}

		principal, ok := authenticator.Authenticate(req.Account, req.Password)
		if !ok {
			writeError(w, r, http.StatusUnauthorized, "AUTH_LOGIN_FAILED", "账号或密码错误", "账号或密码不匹配")
			return
		}

		token, err := tokenManager.GenerateAccessToken(principal.UserID, principal.Username, principal.Role)
		if err != nil {
			writeError(w, r, http.StatusInternalServerError, "INTERNAL_ERROR", "签发 token 失败", err.Error())
			return
		}

		// 设置 cookie（HttpOnly, Secure）
		http.SetCookie(w, &http.Cookie{
			Name:     "access_token",
			Value:    token,
			Path:     "/",
			HttpOnly: true,
			Secure:   false, // 开发环境设为 false，生产环境改为 true
			SameSite: http.SameSiteLaxMode,
			MaxAge:   int(tokenManager.AccessTTLSeconds()),
		})

		writeJSON(w, http.StatusOK, map[string]any{
			"code":    "OK",
			"message": "success",
			"data": loginData{
				AccessToken: token,
				TokenType:   "Bearer",
				ExpiresIn:   tokenManager.AccessTTLSeconds(),
				User: loginUserData{
					ID:       principal.UserID,
					Username: principal.Username,
					Role:     principal.Role,
				},
			},
			"request_id": middleware.GetRequestID(r),
			"timestamp":  time.Now().Format(time.RFC3339),
		})
	}
}
