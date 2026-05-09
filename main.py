"""
main.py - Ana Oyun Döngüsü
============================
Tüm modülleri senkronize ederek oyunu çalıştırır.
"""

import sys
import cv2

from vision_engine import HandTracker
from game_state import GameState, Character
from ai_manager import AdventureAI
from ui_renderer import GameUI


class DnDGame:
    """Webcam kontrollü D&D oyununun ana kontrol sınıfı."""

    WINDOW_NAME = "D&D Macera Oyunu"

    def __init__(self):
        # ----- Modülleri Başlat -----
        print("[*] Kamera başlatılıyor...")
        self.tracker = HandTracker(camera_index=0, dwell_time=2.0)

        print("[*] AI motoru başlatılıyor...")
        self.ai = AdventureAI()

        print("[*] Oyun durumu hazırlanıyor...")
        self.state = GameState(Character(name="Kahraman", char_class="Savaşçı"))

        print("[*] Arayüz hazırlanıyor...")
        self.ui = GameUI(self.tracker.frame_width, self.tracker.frame_height)

        # ----- Açılış Hikayesi Bekletiliyor -----
        print("[*] Tema secimi bekleniyor...")
        self.state.is_theme_selection = True
        self.state.current_story = "Kaderini sec! Yolculugun nerede baslasin?"
        self.state.current_options = {
            "sol_ust": "Karanlik Magara",
            "sag_ust": "Gizemli Orman",
            "sol_alt": "Kaotik Uzay",
            "sag_alt": "Ruhlar Cehennemi"
        }

    def run(self) -> None:
        """Ana oyun döngüsü."""
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_AUTOSIZE)

        try:
            while True:
                # 1) Kameradan kare oku
                frame = self.tracker.read_frame()
                if frame is None:
                    print("[!] Kamera okunamadı.")
                    break

                # 2) Oyun bittiyse
                if self.state.is_game_over:
                    frame = self.ui.draw_game_over(frame, self.state.game_over_reason)
                    cv2.imshow(self.WINDOW_NAME, frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("r"):
                        self._restart()
                    elif key == ord("q"):
                        break
                    continue

                # 3) AI bekleniyor mu?
                if self.state.is_waiting_for_ai:
                    self._check_ai_response()
                    frame = self.ui.draw_overlay(frame, 0.3)
                    frame = self.ui.draw_loading(frame)
                    cv2.imshow(self.WINDOW_NAME, frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4) El takibi
                finger_pos = self.tracker.detect_finger(frame)

                hover_quadrant = None
                progress = 0.0
                selected = None

                if finger_pos:
                    # Buton bölgesinde mi kontrol et
                    btn_qid = self.ui.get_quadrant_from_button(finger_pos[0], finger_pos[1])
                    if btn_qid:
                        # Quadrant enum yerine string kullan
                        from vision_engine import Quadrant
                        qmap = {"sol_ust": Quadrant.SOL_UST, "sag_ust": Quadrant.SAG_UST,
                                "sol_alt": Quadrant.SOL_ALT, "sag_alt": Quadrant.SAG_ALT}
                        q_enum = qmap.get(btn_qid)
                        selected = self.tracker.update_dwell(q_enum)
                        hover_quadrant = btn_qid
                        progress = self.tracker.get_dwell_progress()
                    else:
                        self.tracker.update_dwell(None)
                else:
                    self.tracker.update_dwell(None)

                # 5) Seçim yapıldıysa
                if selected:
                    qid = selected.value
                    choice_text = self.state.current_options.get(qid, "...")
                    print(f"[>] Seçim: {qid} -> {choice_text}")

                    if self.state.is_theme_selection:
                        # Tema secimi yapildi, hikayeyi baslat
                        self.state.current_theme = choice_text
                        self.state.is_theme_selection = False
                        self.state.add_user_choice(f"Tema secildi: {choice_text}")
                        
                        self.state.is_waiting_for_ai = True
                        self.tracker.reset_selection()
                        
                        history = self.state.get_message_history()
                        prompt = f"Oyun basladi! Secilen tema: {choice_text}. {self.state.get_character_summary()}. Buna uygun cok kisa bir acilis hikayesi ver ve ilk aksiyonlari sun."
                        history.append({"role": "user", "content": prompt})
                        self.ai.request_story(history)
                    else:
                        # Normal oyun gidisati
                        prompt = self.state.get_dynamic_prompt(choice_text)
                        self.state.add_user_choice(prompt)
                        self.state.is_waiting_for_ai = True
                        self.tracker.reset_selection()

                        history = self.state.get_message_history()
                        self.ai.request_story(history)

                # 6) Arayüzü çiz
                frame = self.ui.draw_overlay(frame, 0.35)
                frame = self.ui.draw_story_text(frame, self.state.current_story, self.state.current_feedback)
                frame = self.ui.draw_hud(frame, self.state.character.hp, self.state.character.max_hp,
                                         self.state.character.gold, self.state.turn_count, self.state.current_location)
                frame = self.ui.draw_buttons(frame, self.state.current_options, hover_quadrant, progress)

                if finger_pos:
                    frame = self.ui.draw_finger_cursor(frame, finger_pos)

                # El iskeletini çiz
                frame = self.tracker.draw_hand_landmarks(frame)

                cv2.imshow(self.WINDOW_NAME, frame)

                # Çıkış
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        finally:
            self.tracker.release()
            cv2.destroyAllWindows()
            print("[*] Oyun kapatıldı.")

    def _check_ai_response(self) -> None:
        """AI yanıtını kontrol eder ve durumu günceller."""
        if not self.ai.is_requesting():
            response = self.ai.get_last_response()
            error = self.ai.get_last_error()

            if response:
                self.state.update_from_ai_response(response)
                self.state.add_ai_response(str(response))
                self.state.is_waiting_for_ai = False
            elif error:
                print(f"[!] AI hatası: {error}")
                self.state.is_waiting_for_ai = False

    def _restart(self) -> None:
        """Oyunu yeniden başlatır."""
        print("[*] Oyun yeniden başlatılıyor...")
        self.state.reset()
        self.state.is_theme_selection = True
        self.state.current_story = "Kaderini sec! Yolculugun nerede baslasin?"
        self.state.current_options = {
            "sol_ust": "Karanlik Magara",
            "sag_ust": "Gizemli Orman",
            "sol_alt": "Kaotik Uzay",
            "sag_alt": "Ruhlar Cehennemi"
        }


def main():
    print("=" * 50)
    print("  WEBCAM KONTROLLÜ D&D ROL YAPMA OYUNU")
    print("  İşaret parmağınızı butonlarda 2sn bekletin")
    print("  'Q' = Çıkış")
    print("=" * 50)

    try:
        game = DnDGame()
        game.run()
    except KeyboardInterrupt:
        print("\n[*] Oyun kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"\n[!] Hata: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
