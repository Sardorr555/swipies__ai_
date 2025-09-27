import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Alert, AlertDescription } from "./ui/alert";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

interface WaitlistFormData {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  company: string;
  role: string;
  message: string;
}

interface WaitlistResponse {
  success: boolean;
  message: string;
  data?: {
    id: number;
    email: string;
  };
  errors?: Array<{
    field: string;
    message: string;
  }>;
}

export function Waitlist() {
  const [formData, setFormData] = useState<WaitlistFormData>({
    firstName: "",
    lastName: "",
    email: "",
    phone: "",
    company: "",
    role: "",
    message: ""
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState("");

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus('idle');
    setErrorMessage("");

    try {
      const response = await fetch('/api/waitlist', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });

      const result: WaitlistResponse = await response.json();

      if (response.ok && result.success) {
        setSubmitStatus('success');
        setFormData({
          firstName: "",
          lastName: "",
          email: "",
          phone: "",
          company: "",
          role: "",
          message: ""
        });
      } else {
        setSubmitStatus('error');
        if (result.errors && result.errors.length > 0) {
          setErrorMessage(result.errors.map(err => err.message).join(', '));
        } else {
          setErrorMessage(result.message || 'Failed to submit form');
        }
      }
    } catch (error) {
      setSubmitStatus('error');
      setErrorMessage('Network error. Please try again.');
      console.error('Waitlist submission error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setSubmitStatus('idle');
    setErrorMessage("");
  };

  if (submitStatus === 'success') {
    return (
      <Card className="w-full max-w-2xl mx-auto">
        <CardContent className="pt-6">
          <div className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
              <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Спасибо за регистрацию!</h2>
            <p className="text-gray-600 dark:text-gray-300">
              Мы добавили вас в список ожидания. Вы получите уведомление, как только платформа будет готова.
            </p>
            <Button onClick={resetForm} className="w-full">
              Зарегистрировать еще одного пользователя
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="text-3xl font-bold text-center">Присоединяйтесь к Waitlist</CardTitle>
        <CardDescription className="text-center">
          Будьте в числе первых, кто узнает о запуске нашей платформы
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="firstName" className="text-sm font-medium">
                Имя *
              </label>
              <Input
                id="firstName"
                name="firstName"
                type="text"
                placeholder="Введите ваше имя"
                value={formData.firstName}
                onChange={handleInputChange}
                required
              />
            </div>
            
            <div className="space-y-2">
              <label htmlFor="lastName" className="text-sm font-medium">
                Фамилия *
              </label>
              <Input
                id="lastName"
                name="lastName"
                type="text"
                placeholder="Введите вашу фамилию"
                value={formData.lastName}
                onChange={handleInputChange}
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">
              Email *
            </label>
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="your@email.com"
              value={formData.email}
              onChange={handleInputChange}
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="phone" className="text-sm font-medium">
                Телефон
              </label>
              <Input
                id="phone"
                name="phone"
                type="tel"
                placeholder="+7 (999) 123-45-67"
                value={formData.phone}
                onChange={handleInputChange}
              />
            </div>
            
            <div className="space-y-2">
              <label htmlFor="company" className="text-sm font-medium">
                Компания
              </label>
              <Input
                id="company"
                name="company"
                type="text"
                placeholder="Название компании"
                value={formData.company}
                onChange={handleInputChange}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="role" className="text-sm font-medium">
              Роль в компании
            </label>
            <Input
              id="role"
              name="role"
              type="text"
              placeholder="CEO, CTO, Developer, Designer, etc."
              value={formData.role}
              onChange={handleInputChange}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="message" className="text-sm font-medium">
              Дополнительная информация
            </label>
            <Textarea
              id="message"
              name="message"
              placeholder="Расскажите о ваших потребностях или вопросах..."
              value={formData.message}
              onChange={handleInputChange}
              rows={4}
            />
          </div>

          {submitStatus === 'error' && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertDescription>
                {errorMessage}
              </AlertDescription>
            </Alert>
          )}

          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-4">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              Регистрируясь в waitlist, вы соглашаетесь получать уведомления о запуске платформы. 
              Мы не будем спамить и отправим только важные обновления.
            </p>
          </div>

          <Button 
            type="submit" 
            className="w-full"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Отправляем...
              </>
            ) : (
              'Присоединиться к Waitlist'
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
